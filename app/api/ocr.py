import logging
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from app.database.database import get_db
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
    description="Nhận file PDF qua multipart/form-data, trích xuất text trực tiếp hoặc OCR, lưu vào MySQL và trả về JSON.",
)
async def upload_pdf(
    file: UploadFile = File(..., description="File PDF cần xử lý OCR (tối đa 10MB)"),
    db: Session = Depends(get_db),
):
    result = await DocumentService.process_pdf(file=file, db=db)
    return result
