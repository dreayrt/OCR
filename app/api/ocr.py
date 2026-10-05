import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, status
from app.schemas.document import OCRSuccessResponse, OCRErrorResponse
from app.services.document_service import DocumentService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ocr", tags=["OCR"])


@router.post(
    "/pdf",
    response_model=OCRSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": OCRErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": OCRErrorResponse, "description": "File too large"},
        500: {"model": OCRErrorResponse, "description": "Server or OCR processing error"},
    },
    summary="Upload và OCR file PDF 1 trang",
    description="Nhận file PDF qua multipart/form-data, hỗ trợ tùy biến lọc các fields mong muốn (target_fields), trích xuất text và trả về JSON.",
)
async def upload_pdf(
    file: UploadFile = File(..., description="File PDF cần xử lý OCR (tối đa 10MB)"),
    target_fields: Optional[str] = Form(None, description="Danh sách các trường cần lấy, phân cách bằng dấu phẩy. Ví dụ: 'license_type,copyright_owner,distributor,contract_id,issue_date,expiry_date'"),
):
    selected_fields = [f.strip() for f in target_fields.split(",") if f.strip()] if target_fields else None
    result = await DocumentService.process_pdf(file=file, target_fields=selected_fields)
    return result

