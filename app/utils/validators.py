import re
import io
from fastapi import UploadFile, HTTPException, status
from app.config import settings


def validate_pdf_file(file: UploadFile, file_bytes: bytes) -> None:
    """
    Xác thực tính hợp lệ của file upload:
    - Tên file có đuôi .pdf
    - MIME type là application/pdf hoặc octet-stream tương thích
    - Kích thước không vượt quá giới hạn cấu hình
    - File bytes không rỗng và bắt đầu bằng header PDF '%PDF-'
    """
    # 1. Kiểm tra extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_EXTENSION", "message": "Only .pdf files are allowed."},
        )

    # 2. Kiểm tra MIME type
    if file.content_type and file.content_type.lower() not in (
        "application/pdf",
        "application/x-pdf",
        "application/octet-stream",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_MIME_TYPE", "message": f"Invalid MIME type: {file.content_type}. Expected application/pdf."},
        )

    # 3. Kiểm tra kích thước file
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            },
        )

    # 4. Kiểm tra magic bytes của PDF (%PDF-)
    if len(file_bytes) < 5 or not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "CORRUPTED_PDF",
                "message": "File does not appear to be a valid or uncorrupted PDF (missing %PDF- header).",
            },
        )


def validate_pdf_or_image_file(file: UploadFile, file_bytes: bytes) -> str:
    """Validate supported PDF and image license documents."""
    filename = (file.filename or "").lower()
    extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if not file_bytes:
        raise HTTPException(status_code=400, detail={"error_code": "EMPTY_FILE", "message": "The uploaded file is empty."})
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail={"error_code": "FILE_TOO_LARGE", "message": f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."},
        )

    if extension == "pdf":
        validate_pdf_file(file, file_bytes)
        return "pdf"
    if extension in ("png", "jpg", "jpeg"):
        allowed_mimes = {
            "png": ("image/png", "application/octet-stream"),
            "jpg": ("image/jpeg", "application/octet-stream"),
            "jpeg": ("image/jpeg", "application/octet-stream"),
        }
        if file.content_type and file.content_type.lower() not in allowed_mimes[extension]:
            raise HTTPException(status_code=400, detail={"error_code": "INVALID_MIME_TYPE", "message": "Invalid image MIME type."})
        return extension
    raise HTTPException(
        status_code=400,
        detail={"error_code": "UNSUPPORTED_FILE_TYPE", "message": "OCR supports PDF, PNG, and JPG files only."},
    )


def clean_text(text: str) -> str:
    """Làm sạch raw text: chuẩn hóa newline, loại bỏ khoảng trắng thừa và ký tự điều khiển."""
    if not text:
        return ""
    # Chuẩn hóa khoảng trắng và dòng
    text = re.sub(r"[\r\t\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()
