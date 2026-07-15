"""
Chỉ cần sửa danh sách URLS bên dưới rồi bấm Run là crawl toàn bộ,
không cần truyền tham số dòng lệnh.

Luồng chạy:
1. Mở URL đầu tiên trong danh sách.
2. Nếu Cloudflare hiện ra, TỰ TAY giải xong trên cửa sổ Chrome vừa mở.
3. Quay lại terminal/console, nhấn Enter để crawler bắt đầu chạy toàn bộ danh sách URLS.
4. Kết quả được lưu (và ghi đè cập nhật sau mỗi chủ đề) vào file OUTPUT_FILE.
"""

import json

from crawler import create_driver, crawl_questions_from_page
from model import TopicResult


URLS = [
    {
        "title": "Statistical Learning Framework",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-statistical-learning-framework/",
    },
    {
        "title": "Empirical Minimization Framework",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-empirical-minimization-framework/",
    },
    {
        "title": "Linear Regression",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-linear-regression/",
    },
    {
        "title": "Linear Regression – Cost Function",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-linear-regression-cost-function/",
    },
    {
        "title": "Linear Regression – Gradient Descent",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-linear-regression-gradient-descent/",
    },
    {
        "title": "Multivariate Linear Regression",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-multivariate-linear-regression/",
    },
    {
        "title": "Gradient Descent for Multiple Variables",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-gradient-descent-multiple-variables/",
    },
    {
        "title": "Polynomial Regression",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-polynomial-regression/",
    },
    {
        "title": "Logistic Regression",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-logistic-regression/",
    },
    {
        "title": "Hypothesis Representation",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-hypothesis-representation/",
    },
    {
        "title": "Logistic Regression – Decision Boundary",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-logistic-regression-decision-boundary/",
    },
    {
        "title": "Logistic Regression – Cost Function and Gradient Descent",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-logistic-regression-cost-function-gradient-descent/",
    },
    {
        "title": "Logistic Regression – Advanced Optimization",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-logistic-regression-advanced-optimization/",
    },
    {
        "title": "Logistic Regression – Multiple Classification",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-logistic-regression-multiple-classification/",
    },
    {
        "title": "Ensemble Learning – Model Combination Schemes",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-ensemble-learning-model-combination-schemes/",
    },
    {
        "title": "Ensemble Learning",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-ensemble-learning/",
    },
    {
        "title": "Error Correcting Output Codes",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-error-correcting-output-codes/",
    },
    {
        "title": "Boosting Weak Learnability",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-boosting-weak-learnability/",
    },
    {
        "title": "Adaboost Algorithm",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-adaboost-algorithm/",
    },
    {
        "title": "Stacking",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-stacking/",
    },
    {
        "title": "Gradient Descent Algorithm",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-gradient-descent-algorithm/",
    },
    {
        "title": "Subgradient Descent",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-subgradient-descent/",
    },
    {
        "title": "Stochastic Gradient Descent",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-stochastic-gradient-descent/",
    },
    {
        "title": "Stochastic Gradient Descent-2",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-stochastic-gradient-descent-set-2/",
    },
    {
        "title": "SGD Variants",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-sgd-variants/",
    },
    {
        "title": "Kernels",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-kernels/",
    },
    {
        "title": "Kernel Trick",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-kernel-trick/",
    },
    {
        "title": "Support Vector Machines",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-support-vector-machines/",
    },
    {
        "title": "Large Margin Intuition",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-large-margin-intuition/",
    },
    {
        "title": "Margin and Hard SVM",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-margin-hard-svm/",
    },
    {
        "title": " Soft SVM and Norm Regularization",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-soft-svm-norm-regularization/",
    },
    {
        "title": "Optimality Conditions and Support Vectors",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-optimality-conditions-support-vectors/",
    },
    {
        "title": "Implementing Soft SVM with SGD",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-implementing-soft-svm-sgd/",
    },
    {
        "title": "Decision Trees",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-decision-trees/",
    },
    {
        "title": "Gain Measure Implementation",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-decision-trees-gain-measure-implementation/",
    },
    {
        "title": "Decision Tree Pruning",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-decision-trees-pruning/",
    },
    {
        "title": "Decision Tree Pruning - 2",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-decision-trees-pruning-set-2/",
    },
    {
        "title": "Threshold Based Splitting Rules",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-decision-trees-threshold-based-splitting-rules/",
    },
    {
        "title": "Inductive Bias",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-decision-trees-inductive-bias/",
    },
    {
        "title": "Classification Tree",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-classification-tree/",
    },
    {
        "title": "Regression Trees",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-regression-trees/",
    },
    {
        "title": "Random Forest Algorithm",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-random-forest-algorithm/",
    },
    {
        "title": "K-Nearest Neighbor Algorithm",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-k-nearest-neighbor-algorithm/",
    },
    {
        "title": "Nearest Neighbor Analysis",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-nearest-neighbor-analysis/",
    },
    {
        "title": "Naive-Bayes Algorithm",
        "url": "https://www.sanfoundry.com/machine-learning-questions-answers-naive-bayes-algorithm/",
    }
]
 
OUTPUT_FILE = "questions.json"
HEADLESS = False  # Để False vì cần cửa sổ Chrome hiện ra để tự tay giải Cloudflare
DEBUG = False
 
# Major version của Chrome đang cài trên máy bạn (vd: Chrome "145.0.7632.159" -> 145).
# Kiểm tra bằng cách mở Chrome -> chrome://version hoặc chạy `google-chrome --version`.
# Để None thì undetected-chromedriver tự đoán, nhưng đôi khi đoán sai gây lỗi
# "SessionNotCreatedException: This version of ChromeDriver only supports Chrome version X".
CHROME_VERSION_MAIN = 145
# ====================================================
 
 
def main() -> None:
    if not URLS:
        print("Danh sách URLS đang rỗng, hãy thêm ít nhất 1 URL vào biến URLS ở đầu file.")
        return
 
    driver = create_driver(headless=HEADLESS, version_main=CHROME_VERSION_MAIN)
 
    try:
        # --- Mở URL đầu tiên trước để xử lý Cloudflare (nếu có) ---
        first_url = URLS[0]["url"]
        print(f"Đang mở: {first_url}")
        driver.get(first_url)
 
        if not HEADLESS:
            print("Chrome đã mở. Nếu có màn hình xác minh Cloudflare, vui lòng tự tay giải xong.")
            input("Sau khi trang đã tải xong bình thường (đã qua Cloudflare), nhấn Enter để bắt đầu crawl toàn bộ danh sách...")
 
        # --- Crawl từng URL, lưu kết quả sau mỗi bước để không mất dữ liệu nếu lỗi giữa chừng ---
        results = []
        for idx, item in enumerate(URLS):
            print(f"\nĐang cào chủ đề: {item['title']}")
            print(f"URL: {item['url']}")
            questions = crawl_questions_from_page(driver, item["url"], debug=DEBUG)
            print(f"-> Tìm thấy {len(questions)} câu hỏi.")
 
            topic_result = TopicResult(title=item["title"], url=item["url"], questions=questions)
            results.append(topic_result.to_dict())
 
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
 
            # Nghỉ ngẫu nhiên giữa các chủ đề - tránh nhịp chuyển trang đều đặn
            # (dấu hiệu bot) khiến bị chặn kiểu "Sorry, you have been blocked".
            if idx < len(URLS) - 1:
                pause = random.uniform(4, 9)
                print(f"-> Nghỉ {pause:.1f}s trước khi sang chủ đề tiếp theo...")
                time.sleep(pause)
 
        total = sum(r["total_questions"] for r in results)
        print(f"\nHoàn tất! Đã lưu {total} câu hỏi từ {len(results)} chủ đề vào '{OUTPUT_FILE}'")
 
    finally:
        driver.quit()
 
 
if __name__ == "__main__":
    main()