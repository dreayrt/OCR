import logging
from typing import Dict, Any, Optional, List
from fastapi import UploadFile, HTTPException, status

from app.config import settings
from app.utils.validators import validate_pdf_file
from app.utils.file_utils import generate_document_uuid
from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService
from app.services.extraction_service import ExtractionService
from app.schemas.document import ProcessingStatus

logger = logging.getLogger(__name__)


class DocumentService:
    @classmethod
    async def process_pdf(
        cls,
        file: UploadFile,
        target_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        """
        Flow xử lý chính của OCR Service (Stateless Microservice):
        1. Đọc stream bytes từ memory
        2. Validate định dạng, size, MIME type
        3. Khởi tạo document UUID
        4. Thử trích xuất text trực tiếp bằng PyMuPDF
           - Nếu có text: dùng trực tiếp, KHÔNG gọi PaddleOCR
           - Nếu không có text (PDF scan): render 200 DPI và gửi mảng ảnh vào PaddleOCR
        5. Trích xuất structured data (Rule/Regex) theo target_fields
        6. Trả về kết quả JSON chuẩn hóa cho client
        """
        # Đọc dữ liệu trực tiếp trong memory, không ghi đĩa
        try:
            file_bytes = await file.read()
        except Exception as e:
            logger.error(f"Failed to read uploaded file: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "FILE_READ_ERROR", "message": "Could not read uploaded file content."},
            )

        # 1. Validation
        validate_pdf_file(file, file_bytes)
        document_uuid = generate_document_uuid()
        file_size = len(file_bytes)
        mime_type = file.content_type or "application/pdf"
        original_filename = file.filename or "unknown.pdf"

        logger.info(f"Processing document [{document_uuid}] - {original_filename} ({file_size} bytes)")

        # 2. Xử lý PDF và Text Extraction
        raw_text = ""
        ocr_engine = "direct_text"
        ocr_confidence = 1.0

        try:
            direct_text, img_np, is_ocr_needed = PDFService.inspect_and_extract_page(file_bytes)

            if not is_ocr_needed:
                # Trích xuất text trực tiếp thành công
                raw_text = direct_text
                ocr_engine = "direct_text"
                ocr_confidence = 1.0
            else:
                # Fallback sang PaddleOCR
                ocr_service = OCRService.get_instance()
                raw_text, ocr_confidence = ocr_service.ocr_image(img_np)
                ocr_engine = "paddleocr"

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Processing failed for document [{document_uuid}]: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error_code": "OCR_PROCESSING_FAILED", "message": f"Failed during text extraction: {str(e)}"},
            )

        # 3. Trích xuất Structured Data
        extracted_fields, field_confidences = ExtractionService.extract_fields(
            raw_text, base_confidence=ocr_confidence
        )

        # Lọc danh sách fields nếu client chỉ định target_fields cụ thể
        if target_fields:
            extracted_fields = {k: v for k, v in extracted_fields.items() if k in target_fields}
            field_confidences = {k: v for k, v in field_confidences.items() if k in target_fields}


        logger.info(f"Successfully processed document [{document_uuid}] with {len(extracted_fields)} fields.")

        return {
            "success": True,
            "document_uuid": document_uuid,
            "processing_status": ProcessingStatus.COMPLETED.value,
            "ocr_engine": ocr_engine,
            "raw_text": raw_text,
            "extracted_fields": extracted_fields,
            "confidence": round(ocr_confidence, 2),
        }

