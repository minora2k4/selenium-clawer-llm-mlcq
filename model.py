from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class Question:
    """Một câu hỏi trắc nghiệm đã crawl được."""
    question: str
    options: List[str] = field(default_factory=list)
    answer: str = ""
    explanation: str = ""
    # URL gốc của trang chứa câu hỏi này. Dùng khi câu hỏi có hình ảnh
    # (biểu đồ, sơ đồ...) mà text không thể hiện hết -> mở URL này để xem ảnh gốc.
    source_url: str = ""
    # True nếu phát hiện có ảnh (không phải công thức toán) trong câu hỏi/đáp án.
    has_image: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TopicResult:
    """Kết quả crawl của một chủ đề con (1 URL)."""
    title: str
    url: str
    questions: List[Question] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "total_questions": len(self.questions),
            "questions": [q.to_dict() for q in self.questions],
        }