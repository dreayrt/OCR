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
    summary="Trích xuất thông tin từ PDF hoặc hình ảnh bản quyền",
    description="Nhận PDF, PNG hoặc JPG qua multipart/form-data, trích xuất văn bản và trả về các trường được yêu cầu.",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF, PNG hoặc JPG (tối đa 10MB)"),
    target_fields: Optional[str] = Form(None, description="Danh sách các trường cần lấy, phân cách bằng dấu phẩy. Ví dụ: 'license_type,copyright_owner,distributor,contract_id,issue_date,expiry_date'"),
):
    selected_fields = [f.strip() for f in target_fields.split(",") if f.strip()] if target_fields else None
    result = await DocumentService.process_pdf(file=file, target_fields=selected_fields)
    return result

