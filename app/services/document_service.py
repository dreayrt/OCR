import logging
import io
from typing import Dict, Any, Optional, List
from fastapi import UploadFile, HTTPException, status
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.utils.validators import validate_pdf_or_image_file
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
        document_format = validate_pdf_or_image_file(file, file_bytes)
        document_uuid = generate_document_uuid()
        file_size = len(file_bytes)
        mime_type = file.content_type or "application/octet-stream"
        original_filename = file.filename or "unknown.pdf"

        logger.info(f"Processing document [{document_uuid}] - {original_filename} ({file_size} bytes)")

        # 2. Extract native text where available; use PaddleOCR for scans/images
        raw_text = ""
        ocr_engine = "direct_text"
        ocr_confidence = 1.0

        try:
            if document_format == "pdf":
                page_texts = []
                page_confidences = []
                for page_number, direct_text, img_np in PDFService.inspect_and_extract_pages(file_bytes):
                    if img_np is not None:
                        scanned_text, page_confidence = OCRService.get_instance().ocr_image(img_np)
                        direct_text = "\n".join(part for part in (direct_text, scanned_text) if part)
                        page_confidences.append(page_confidence)
                        ocr_engine = "hybrid" if page_texts else "paddleocr"
                    page_texts.append(f"--- PAGE {page_number} ---\n{direct_text}")
                raw_text = "\n".join(page_texts)
                if page_confidences:
                    ocr_confidence = min(page_confidences)
            else:
                try:
                    with Image.open(io.BytesIO(file_bytes)) as image:
                        image.verify()
                    with Image.open(io.BytesIO(file_bytes)) as image:
                        if image.width * image.height > 40_000_000:
                            raise HTTPException(
                                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail={"error_code": "IMAGE_TOO_LARGE", "message": "Image dimensions exceed the OCR limit."},
                            )
                        img_np = np.asarray(image.convert("RGB"))
                except (UnidentifiedImageError, OSError) as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"error_code": "INVALID_IMAGE", "message": "The uploaded image is invalid or corrupted."},
                    ) from e
                ocr_service = OCRService.get_instance()
                raw_text, ocr_confidence = ocr_service.ocr_image(img_np)
                ocr_engine = "paddleocr"
                raw_text = f"--- PAGE 1 ---\n{raw_text}"

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
        cost_evidence = ExtractionService.extract_acquisition_cost(raw_text)
        field_evidence = {"acquisition_cost_vnd": cost_evidence} if cost_evidence else {}

        # Lọc danh sách fields nếu client chỉ định target_fields cụ thể
        if target_fields:
            extracted_fields = {k: v for k, v in extracted_fields.items() if k in target_fields}
            field_confidences = {k: v for k, v in field_confidences.items() if k in target_fields}
            field_evidence = {k: v for k, v in field_evidence.items() if k in target_fields}


        logger.info(f"Successfully processed document [{document_uuid}] with {len(extracted_fields)} fields.")

        return {
            "success": True,
            "document_uuid": document_uuid,
            "processing_status": ProcessingStatus.COMPLETED.value,
            "ocr_engine": ocr_engine,
            "raw_text": raw_text,
            "extracted_fields": extracted_fields,
            "field_evidence": field_evidence,
            "confidence": round(ocr_confidence, 2),
        }
