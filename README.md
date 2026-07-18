# MLCQ — Machine Learning MCQ

Bộ câu hỏi trắc nghiệm ôn tập Machine Learning, được crawl tự động từ [Sanfoundry](https://www.sanfoundry.com/), dịch sang tiếng Việt bằng LLM, và phục vụ qua một web app tĩnh để luyện tập.

Pipeline gồm 3 bước, tương ứng với 3 phần trong dự án:

```
crawl (Selenium)  →  translate (OpenRouter LLM)  →  app (web quiz)
```

## Cấu trúc thư mục

```
.
├── app/                          # Web app luyện quiz (static site)
│   ├── index.html
│   ├── style.css
│   └── script.js
├── output/                       # Dữ liệu câu hỏi (đầu ra của từng bước)
│   ├── questions.json            # Kết quả crawl thô (tiếng Anh)
│   └── questions_translated.json # Kết quả sau khi dịch (đã có tiếng Việt), app đọc trực tiếp file này
├── process_data/
│   ├── crawler.ipynb             # Bước 1: crawl câu hỏi từ Sanfoundry
│   └── translate.ipynb           # Bước 2: dịch câu hỏi sang tiếng Việt
└── requirements.txt              # Thư viện Python cần cho crawler + translate
```

## 1. Crawler — `process_data/crawler.ipynb`

- Dùng **Selenium** để duyệt và trích xuất câu hỏi trắc nghiệm Machine Learning từ [sanfoundry.com](https://www.sanfoundry.com/).
- Với mỗi chủ đề (ví dụ: Linear Regression, Logistic Regression, SVM, Decision Trees, Ensemble Learning...), crawler lấy: câu hỏi, các lựa chọn, đáp án đúng, và phần giải thích.
- Kết quả được ghi ra `output/questions.json` theo cấu trúc:
  ```json
  {
    "title": { "0": "Tên chủ đề 1", "1": "Tên chủ đề 2", ... },
    "html":  { "0": [ { "question": "...", "options": {"a": "...", "b": "..."}, "answer": "b", "explanation": "..." } ] }
  }
  ```

> Lưu ý: vì phụ thuộc cấu trúc HTML của Sanfoundry, một số câu hỏi có thể bị crawl thiếu lựa chọn (đặc biệt các câu Đúng/Sai). Web app ở bước 3 tự động phát hiện và bù lại các câu này khi tải dữ liệu, nên không cần crawl/dịch lại.

## 2. Translate — `process_data/translate.ipynb`

- Đọc `output/questions.json`, dịch toàn bộ câu hỏi, lựa chọn và giải thích từ tiếng Anh sang tiếng Việt.
- Sử dụng **LLM miễn phí thông qua [OpenRouter](https://openrouter.ai/)** để dịch (thay vì các API dịch trả phí).
- Kết quả ghi ra `output/questions_translated.json` — giữ nguyên cấu trúc như bản gốc, chỉ thay nội dung text bằng bản dịch tiếng Việt.
- Cần có API key OpenRouter (thường cấu hình qua biến môi trường, ví dụ `OPENROUTER_API_KEY`) trước khi chạy notebook.

## 3. Web app — `app/`

Một trang web tĩnh (không cần backend) để luyện tập với bộ câu hỏi đã dịch, gồm 3 file thuần HTML/CSS/JS — không dùng framework, không cần build:

| File | Vai trò |
|---|---|
| `index.html` | Khung trang, nạp `style.css` và `script.js` |
| `style.css` | Toàn bộ giao diện |
| `script.js` | Tải dữ liệu từ `../output/questions_translated.json`, tự sửa các câu bị thiếu lựa chọn, và xử lý toàn bộ logic quiz |

**Tính năng:**
- **Quiz đầy đủ** — làm hết toàn bộ câu hỏi, thứ tự xáo trộn.
- **Mini Quiz** — 5 câu ngẫu nhiên mỗi chủ đề, phủ nhanh toàn bộ nội dung.
- **Ôn theo chủ đề** — chọn từng chủ đề để luyện riêng.
- Điều hướng tự do giữa các câu, đánh dấu câu đã trả lời, nộp bài bất cứ lúc nào.
- Sau khi nộp: điểm số tổng, phân tích đúng/sai theo chủ đề, danh sách review từng câu (đáp án bạn chọn / đáp án đúng / giải thích), lọc theo "câu sai" / "câu đúng".
- Lưu lịch sử các lượt làm bài trên trình duyệt (`localStorage`), không gửi dữ liệu lên server nào.

## Cách chạy

### Cài đặt (chỉ cần cho crawl/translate)

```bash
pip install -r requirements.txt
```

Chạy lần lượt 2 notebook trong `process_data/` (crawler trước, translate sau) để tạo/cập nhật dữ liệu trong `output/`. Nếu bạn chỉ muốn dùng lại bộ câu hỏi có sẵn, có thể bỏ qua bước này.

### Chạy web app

`script.js` dùng `fetch()` để đọc `output/questions_translated.json`, nên cần mở qua HTTP (mở trực tiếp file bằng double-click sẽ bị trình duyệt chặn vì CORS):

```bash
# chạy ở thư mục gốc dự án (chỗ chứa cả app/ và output/)
python3 -m http.server 8000
```

Sau đó mở: **http://localhost:8000/app/index.html**

Để dùng trên điện thoại cùng mạng LAN, thay `localhost` bằng địa chỉ IP của máy tính, ví dụ `http://192.168.1.5:8000/app/index.html`.

## Cập nhật dữ liệu

Vì web app đọc trực tiếp `output/questions_translated.json` mỗi lần tải trang, bạn có thể crawl thêm chủ đề mới hoặc dịch lại bất cứ lúc nào — chỉ cần ghi đè file này rồi refresh trang, không cần build lại app.
