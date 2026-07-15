"""
crawler.py
Chứa toàn bộ logic Selenium + BeautifulSoup để lấy danh sách chủ đề con
và cào câu hỏi/đáp án/giải thích từ một trang sanfoundry.

Các điểm xử lý đặc biệt:
- Giữ lại công thức toán học (tích phân, sigma, LaTeX...) thay vì bị mất khi
  BeautifulSoup .get_text() bỏ qua nội dung trong <img>/<script>/<math>.
- Tự động dọn/đóng overlay quảng cáo hay che trang mỗi khi chuyển URL.
- Mỗi câu hỏi có thêm "source_url" (link tới trang gốc) để tiện mở xem
  hình ảnh gốc nếu câu hỏi có ảnh minh họa.
"""

import random
import re
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from model import Question


def _human_delay(min_seconds: float, max_seconds: float) -> None:
    """Nghỉ 1 khoảng thời gian ngẫu nhiên - tránh nhịp thao tác đều tăm tắp
    (dấu hiệu bot rõ ràng mà Cloudflare bot-management theo dõi)."""
    time.sleep(random.uniform(min_seconds, max_seconds))


def create_driver(headless: bool = False, version_main: Optional[int] = None) -> uc.Chrome:
    """Khởi tạo Chrome driver bằng undetected-chromedriver (uc).

    Trước đây dùng selenium.webdriver.Chrome thường + vá thủ công vài flag/CDP,
    nhưng Cloudflare hiện đại vẫn phát hiện được qua nhiều lớp fingerprint khác
    (CDP traces, chữ ký binary chromedriver...) nên vẫn bị bắt xác minh lặp lại.
    undetected-chromedriver vá sâu hơn ở cấp binary/CDP nên hiệu quả hơn nhiều
    với Cloudflare. Không đảm bảo bypass 100%, nhưng giảm mạnh tình trạng lặp
    captcha liên tục.

    version_main: major version của Chrome đang cài trên máy (ví dụ 145 nếu
    Chrome là "145.0.7632.159"). Nên truyền rõ giá trị này, vì nếu để None,
    undetected-chromedriver có thể tự tải nhầm bản ChromeDriver không khớp
    phiên bản Chrome thật -> lỗi "SessionNotCreatedException: This version
    of ChromeDriver only supports Chrome version X"."""
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(
        options=options,
        headless=headless,
        use_subprocess=True,
        version_main=version_main,
    )

    # Ghi đè navigator.webdriver = undefined TRƯỚC KHI bất kỳ trang nào chạy
    # JS của nó (kể cả trang đầu tiên) - đây là cờ hiệu quan trọng nhất mà
    # Cloudflare kiểm tra.
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                """
            },
        )
    except Exception:
        pass

    return driver


def get_sub_urls(driver: uc.Chrome, main_url: str) -> List[Dict[str, str]]:
    """Lấy danh sách link chủ đề con từ trang mục lục chính."""
    driver.get(main_url)
    soup_main = BeautifulSoup(driver.page_source, "lxml")

    content_div = soup_main.find("div", class_="entry-content")
    sub_urls: List[Dict[str, str]] = []
    if not content_div:
        return sub_urls

    for link in content_div.find_all("a"):
        href = link.get("href")
        if not href:
            continue
        full_url = urljoin(main_url, href)
        if "machine-learning" in full_url and full_url != main_url:
            sub_urls.append({"title": link.get_text(strip=True), "url": full_url})

    return sub_urls


# ============================================================
# XỬ LÝ OVERLAY QUẢNG CÁO
# ============================================================

def dismiss_overlays(driver: uc.Chrome) -> None:
    """Cố gắng đóng các overlay/quảng cáo/pop-up hay che khuất trang mỗi khi
    chuyển sang URL mới. Chạy nhiều "chiến thuật" khác nhau, cái nào lỗi thì
    bỏ qua (không làm crash crawler)."""

    # 1. Bấm ESC - nhiều modal/overlay đóng khi nhận phím này
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass

    # 2. Tìm và bấm các nút "đóng" phổ biến (class chứa close/dismiss, aria-label Close, hoặc chữ × / X)
    close_selectors = [
        "//*[self::button or self::a or self::span or self::div]"
        "[contains(@class,'close') or contains(@class,'dismiss')]",
        "//*[@aria-label='Close' or @aria-label='close' or @aria-label='Đóng']",
        "//*[self::button or self::a][normalize-space(text())='×' or normalize-space(text())='X' "
        "or normalize-space(text())='Close' or normalize-space(text())='Đóng']",
    ]
    for selector in close_selectors:
        try:
            for btn in driver.find_elements(By.XPATH, selector):
                try:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    pass
        except Exception:
            pass

    # 3. Dọn "cứng" mọi phần tử fixed/sticky có z-index cao đang phủ lên trang
    #    (kiểu overlay quảng cáo toàn màn hình, sticky ad bar...) bằng cách xóa
    #    thẳng khỏi DOM. An toàn hơn việc click bừa vì không lỡ mở link quảng cáo.
    try:
        driver.execute_script(
            """
            document.querySelectorAll('body *').forEach(function(el) {
                var style = window.getComputedStyle(el);
                var z = parseInt(style.zIndex) || 0;
                if ((style.position === 'fixed' || style.position === 'sticky') && z > 999) {
                    el.remove();
                }
            });
            """
        )
    except Exception:
        pass


# ============================================================
# TRÍCH XUẤT TEXT CÓ GIỮ CÔNG THỨC TOÁN HỌC
# ============================================================

_MATH_CLASS_HINTS = ("latex", "tex", "mathml", "quicklatex", "mathjax")


def _looks_like_math(text: str, css_class: str) -> bool:
    if not text:
        return False
    if "\\" in text or "$" in text:
        return True
    return any(hint in css_class.lower() for hint in _MATH_CLASS_HINTS)


def _extract_node(node) -> str:
    """Đệ quy lấy text của 1 node, giữ lại công thức toán, thay ảnh thường
    bằng placeholder để biết có ảnh (xem thêm ở source_url)."""
    if isinstance(node, NavigableString):
        return str(node)

    if not isinstance(node, Tag):
        return ""

    # MathJax render bằng <script type="math/tex">...</script> -> LaTeX gốc
    if node.name == "script":
        node_type = (node.get("type") or "").lower()
        if node_type.startswith("math/tex"):
            latex = node.get_text(strip=True)
            return f" ${latex}$ "
        return ""  # bỏ qua các <script> khác

    # MathML <math>...<annotation encoding="application/x-tex">LaTeX</annotation></math>
    if node.name == "math":
        annotation = node.find("annotation", attrs={"encoding": "application/x-tex"})
        if annotation and annotation.get_text(strip=True):
            return f" ${annotation.get_text(strip=True)}$ "
        return f" {node.get_text(' ', strip=True)} "

    # Công thức toán render bằng ảnh (QuickLaTeX, WP-LaTeX...): alt/title chứa mã LaTeX
    if node.name == "img":
        css_class = " ".join(node.get("class") or [])
        candidate = (node.get("alt") or "").strip() or (node.get("title") or "").strip()
        if _looks_like_math(candidate, css_class):
            return f" ${candidate}$ "
        # Ảnh thường (hình minh họa, biểu đồ...) -> không có text để lấy,
        # đánh dấu bằng placeholder, người dùng xem ảnh gốc qua source_url.
        return " [Hình ảnh - xem ảnh gốc tại source_url] "

    # Các thẻ khác: đệ quy vào bên trong
    return "".join(_extract_node(child) for child in node.children)


def get_text_with_math(tag: Tag) -> str:
    """Thay thế cho tag.get_text(' ', strip=True) nhưng giữ lại công thức
    toán học (tích phân, sigma, phân số...) dưới dạng LaTeX thay vì làm mất
    hoàn toàn nội dung công thức."""
    raw = _extract_node(tag)
    return re.sub(r"\s+", " ", raw).strip()


def get_lines_with_math(tag: Tag) -> List[str]:
    """Thay thế cho tag.get_text('\\n').split('\\n') (dùng để tách dòng
    "Answer: ..." / "Explanation: ...") nhưng:
    - Ranh giới 1 "dòng" là thẻ <br> hoặc các thẻ <p>/<div> con.
    - Text + công thức toán nằm liền nhau trên cùng 1 dòng được GỘP lại
      (không bị vỡ vụn theo từng text-node như cách làm get_text('\\n') gốc),
      để 1 câu giải thích có công thức toán ở giữa câu không bị cắt mất phần sau.
    """
    lines: List[str] = []
    current_parts: List[str] = []

    def flush():
        joined = re.sub(r"[ \t]+", " ", "".join(current_parts)).strip()
        if joined:
            lines.append(joined)
        current_parts.clear()

    def walk(node):
        if isinstance(node, NavigableString):
            current_parts.append(str(node))
            return
        if not isinstance(node, Tag):
            return
        if node.name == "br":
            flush()
            return
        if node.name in ("p", "div") and node is not tag:
            flush()
            current_parts.append(_extract_node(node))
            flush()
            return
        # script/math/img: tái sử dụng logic của _extract_node cho từng loại
        if node.name in ("script", "math", "img"):
            current_parts.append(_extract_node(node))
            return
        for child in node.children:
            walk(child)

    for child in tag.children:
        walk(child)
    flush()
    return lines


def has_content_image(tag: Tag) -> bool:
    """True nếu trong tag có ảnh KHÔNG phải công thức toán (ảnh minh họa thật)."""
    for img in tag.find_all("img"):
        css_class = " ".join(img.get("class") or [])
        candidate = (img.get("alt") or "").strip() or (img.get("title") or "").strip()
        if not _looks_like_math(candidate, css_class):
            return True
    return False


def _classes_contain(tag: Tag, keyword: str) -> bool:
    """Kiểm tra tag có class nào CHỨA keyword (substring match, không phải
    so khớp tuyệt đối - đây là bug đã sửa so với bản gốc)."""
    classes = tag.get("class") or []
    return any(keyword in c for c in classes)


def _extract_bold_answer(tag: Tag) -> Optional[str]:
    """Nếu đáp án đúng được đánh dấu in đậm (<b>/<strong>) trong tag, trả về chữ cái a-d."""
    bold_tag = tag.find(["b", "strong"])
    if not bold_tag:
        return None
    btxt = get_text_with_math(bold_tag)
    m = re.match(r"^([a-dA-D])\)", btxt)
    return m.group(1).lower() if m else None


# ============================================================
# CRAWL CHÍNH
# ============================================================

def crawl_questions_from_page(
    driver: uc.Chrome, url: str, debug: bool = False
) -> List[Question]:
    """Cào toàn bộ câu hỏi/đáp án/giải thích từ một trang chủ đề."""
    driver.get(url)
    _human_delay(2.5, 4.5)  # thời gian tải trang ngẫu nhiên, tránh đều tăm tắp như bot

    # Dọn overlay quảng cáo ngay sau khi trang vừa load, trước khi thao tác
    dismiss_overlays(driver)

    # --- BƯỚC 1: Mở tất cả các "View Answer" ---
    view_answer_buttons = driver.find_elements(
        By.XPATH,
        "//*[contains(@class, 'collapseomatic') and not(contains(@class, 'collapseomatic_content'))]",
    )
    if not view_answer_buttons:
        view_answer_buttons = driver.find_elements(
            By.XPATH, "//*[contains(text(), 'View Answer')]"
        )

    print(f"-> Đang mở {len(view_answer_buttons)} đáp án ẩn tìm thấy trên trang: {url}")
    for i, btn in enumerate(view_answer_buttons):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            _human_delay(0.2, 0.6)
            # Ưu tiên click "thật" (giả lập sự kiện chuột như người dùng) thay vì
            # chỉ dùng JS execute_script click - JS click hàng loạt cực nhanh là
            # dấu hiệu bot rõ rệt mà Cloudflare bot-management theo dõi được.
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
            _human_delay(0.15, 0.5)
        except Exception:
            pass

        # Overlay quảng cáo có thể bất ngờ xuất hiện trong lúc cuộn/click -> dọn định kỳ
        if i % 15 == 0:
            dismiss_overlays(driver)

    _human_delay(1.0, 2.0)  # Chờ hiệu ứng hiển thị hoàn tất
    dismiss_overlays(driver)  # dọn lần cuối trước khi lấy page_source để parse

    # --- BƯỚC 2: Bóc tách dữ liệu ---
    soup = BeautifulSoup(driver.page_source, "lxml")
    entry_content = soup.find("div", class_="entry-content")

    questions_data: List[Question] = []
    if not entry_content:
        return questions_data

    if debug:
        print(entry_content.prettify()[:3000])

    elements = entry_content.find_all(["p", "div"], recursive=False)
    current_question: Optional[Question] = None

    for element in elements:
        text = get_text_with_math(element)
        if not text:
            continue

        # 1. Câu hỏi mới (bắt đầu bằng "số + dấu chấm")
        if element.name == "p" and re.match(r"^\d+\.", text):
            if current_question:
                questions_data.append(current_question)

            clean_text = text.replace("View Answer", "").strip()
            first_opt_match = re.search(r"\ba\)\s", clean_text)

            question_body = clean_text
            options_list: List[str] = []

            if first_opt_match:
                split_idx = first_opt_match.start()
                question_body = clean_text[:split_idx].strip()
                options_part = clean_text[split_idx:].strip()

                opt_markers = list(re.finditer(r"\b([a-d])\)\s", options_part))
                for i in range(len(opt_markers)):
                    start = opt_markers[i].start()
                    end = (
                        opt_markers[i + 1].start()
                        if i + 1 < len(opt_markers)
                        else len(options_part)
                    )
                    options_list.append(options_part[start:end].strip())

            current_question = Question(
                question=question_body,
                options=options_list,
                source_url=url,
                has_image=has_content_image(element),
            )

            bold_answer = _extract_bold_answer(element)
            if bold_answer:
                current_question.answer = bold_answer

        # 2. Phương án nằm ở các thẻ <p> độc lập tiếp theo
        elif element.name == "p" and current_question and re.match(r"^[a-d]\)", text):
            clean_opt = text.replace("View Answer", "").strip()
            if clean_opt not in current_question.options:
                current_question.options.append(clean_opt)

            if has_content_image(element):
                current_question.has_image = True

            if not current_question.answer:
                bold_answer = _extract_bold_answer(element)
                if bold_answer:
                    current_question.answer = bold_answer

        # 3. Đáp án + giải thích từ khối ẩn (đã hiện ra sau khi click)
        elif element.name == "div" and current_question and (
            _classes_contain(element, "collapse") or _classes_contain(element, "sf-show")
        ):
            if has_content_image(element):
                current_question.has_image = True

            lines = get_lines_with_math(element)
            for line in lines:
                low = line.lower()
                if low.startswith("answer:"):
                    current_question.answer = line.split(":", 1)[1].strip()
                elif low.startswith("explanation:"):
                    current_question.explanation = line.split(":", 1)[1].strip()

            if not current_question.answer:
                bold_answer = _extract_bold_answer(element)
                if bold_answer:
                    current_question.answer = bold_answer

    if current_question:
        questions_data.append(current_question)

    return questions_data