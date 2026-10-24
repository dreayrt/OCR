import logging
from typing import Tuple, Optional
import fitz  # PyMuPDF
import numpy as np
from fastapi import HTTPException, status
from app.config import settings
from app.utils.validators import clean_text

logger = logging.getLogger(__name__)


class PDFService:
    @staticmethod
    def inspect_and_extract_pages(file_bytes: bytes):
        """Yield native text or a rendered image for each PDF page."""
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            raise HTTPException(status_code=400, detail={"error_code": "INVALID_PDF", "message": str(exc)}) from exc
        try:
            if doc.is_encrypted or doc.page_count < 1:
                raise HTTPException(status_code=400, detail={"error_code": "INVALID_PDF", "message": "PDF is encrypted or empty."})
            if doc.page_count > settings.PDF_MAX_PAGES:
                raise HTTPException(status_code=413, detail={"error_code": "TOO_MANY_PAGES", "message": f"PDF exceeds {settings.PDF_MAX_PAGES} pages."})
            for index, page in enumerate(doc):
                direct_text = clean_text(page.get_text("text") or "")
                # A PDF may have searchable contract text but a scanned price table.
                # OCR pages with embedded images as well, keeping the native text.
                if len(direct_text) >= settings.MIN_TEXT_LENGTH_THRESHOLD and not page.get_images(full=True):
                    yield index + 1, direct_text, None
                    continue
                pix = page.get_pixmap(matrix=fitz.Matrix(settings.PDF_RENDER_DPI / 72.0, settings.PDF_RENDER_DPI / 72.0), alpha=False)
                image = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
                if pix.n == 4:
                    image = image[:, :, :3]
                elif pix.n == 1:
                    image = np.repeat(image, 3, axis=2)
                yield index + 1, direct_text, image
        finally:
            doc.close()

    @staticmethod
    def inspect_and_extract_page(
        file_bytes: bytes,
    ) -> Tuple[str, Optional[np.ndarray], bool]:
        """
        Mở PDF từ memory và xử lý trang đầu tiên:
        - Kiểm tra tính toàn vẹn và bảo mật của PDF
        - Thử trích xuất text trực tiếp từ text layer (page.get_text)
        - Nếu text hợp lệ (độ dài >= MIN_TEXT_LENGTH_THRESHOLD):
            -> trả về (text, None, False) -> KHÔNG cần OCR
        - Nếu text rỗng hoặc không khả dụng (PDF scan):
            -> render trang 1 với độ phân giải DPI cấu hình (mặc định 200 DPI)
            -> trả về ("", image_np, True) -> Fallback sang PaddleOCR

        Returns:
            Tuple[raw_text, image_numpy_array, is_ocr_needed]
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"Cannot open PDF stream: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "INVALID_PDF", "message": f"Unable to parse PDF: {str(e)}"},
            )

        try:
            if doc.is_encrypted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "PDF_ENCRYPTED",
                        "message": "PDF is password-protected or encrypted.",
                    },
                )

            if doc.page_count < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "EMPTY_PDF",
                        "message": "PDF contains no pages.",
                    },
                )

            # Lấy trang đầu tiên (hệ thống chuyên cho tài liệu 1 trang)
            page = doc[0]

            # 1. Ưu tiên trích xuất text trực tiếp từ PyMuPDF
            direct_text = page.get_text("text") or ""
            direct_text = clean_text(direct_text)

            if len(direct_text) >= settings.MIN_TEXT_LENGTH_THRESHOLD:
                logger.info(
                    f"Direct text extraction successful ({len(direct_text)} chars). Skipping PaddleOCR."
                )
                return direct_text, None, False

            logger.info(
                f"Direct text extraction yielded insufficient text ({len(direct_text)} chars). Rendering page at {settings.PDF_RENDER_DPI} DPI for OCR fallback."
            )

            # 2. Render trang thành image ở độ phân giải 200 DPI (72 pt = 1 inch tiêu chuẩn PDF)
            dpi = settings.PDF_RENDER_DPI
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)

            # Chuyển đổi PyMuPDF pixmap sang numpy array (RGB) mà KHÔNG cần OpenCV
            # pix.samples là raw bytes
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))

            # Đảm bảo định dạng RGB 3 kênh
            if pix.n == 4:
                img_np = img_np[:, :, :3]
            elif pix.n == 1:
                img_np = np.repeat(img_np, 3, axis=2)

            return "", img_np, True

        finally:
            doc.close()
