import logging
from typing import Tuple, Optional
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)


class OCRService:
    """
    OCR Engine Wrapper sử dụng PaddleOCR.
    - Singleton instance được nạp một lần duy nhất khi startup.
    - Không sử dụng OpenCV hay bất kỳ image preprocessing phức tạp nào.
    - Đưa trực tiếp numpy array từ render PDF vào PaddleOCR.
    """

    _instance: Optional["OCRService"] = None
    _engine = None

    def __init__(self):
        self._init_engine()

    @classmethod
    def get_instance(cls) -> "OCRService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_engine(self):
        """Khởi tạo PaddleOCR model với ngôn ngữ cấu hình (ưu tiên tiếng Việt 'vi')."""
        try:
            from paddleocr import PaddleOCR

            logger.info(f"Initializing PaddleOCR engine with language '{settings.OCR_LANGUAGE}'...")
            # use_angle_cls=False hoặc True tùy cấu hình, dùng use_gpu=False để chạy ổn định trên CPU container
            self._engine = PaddleOCR(
                use_angle_cls=False,
                lang=settings.OCR_LANGUAGE,
                show_log=False,
            )
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR engine: {e}")
            self._engine = None

    def ocr_image(self, img_np: np.ndarray) -> Tuple[str, float]:
        """
        Thực hiện OCR trực tiếp trên mảng numpy hình ảnh:
        - Không áp dụng OpenCV tiền xử lý (denoise, sharpen, deskew...)
        - Trả về text tổng hợp và confidence trung bình
        """
        if self._engine is None:
            # Thử tái khởi tạo nếu chưa có
            self._init_engine()
            if self._engine is None:
                raise RuntimeError("PaddleOCR engine is not available or failed to initialize.")

        try:
            logger.info("Starting PaddleOCR recognition on image...")
            result = self._engine.ocr(img_np, cls=False)

            text_lines = []
            confidences = []

            # Kết quả PaddleOCR có dạng: [[ [box, (text, conf)], ... ]]
            if result and len(result) > 0 and result[0] is not None:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_info = line[1]
                        recognized_text = text_info[0].strip()
                        conf = float(text_info[1])
                        if recognized_text:
                            text_lines.append(recognized_text)
                            confidences.append(conf)

            full_text = "\n".join(text_lines)
            avg_confidence = float(np.mean(confidences)) if confidences else 0.0
            logger.info(
                f"OCR completed: {len(text_lines)} lines detected, avg confidence: {avg_confidence:.2f}"
            )
            return full_text, round(avg_confidence, 4)

        except Exception as e:
            logger.error(f"PaddleOCR recognition failed: {e}")
            raise RuntimeError(f"OCR processing failed: {str(e)}")
