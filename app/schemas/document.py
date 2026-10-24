import enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class HealthResponse(BaseModel):
    status: str = "UP"


class FieldDetail(BaseModel):
    value: Any
    confidence: float = 1.0


class OCRSuccessResponse(BaseModel):
    success: bool = True
    document_uuid: str
    processing_status: str
    ocr_engine: Optional[str] = "direct_text"
    raw_text: Optional[str] = None
    extracted_fields: Dict[str, Any]
    field_evidence: Dict[str, Any] = Field(default_factory=dict)
    confidence: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "document_uuid": "c3a52753-8a57-4d55-aae1-1e525de7bd87",
                "processing_status": "COMPLETED",
                "ocr_engine": "direct_text",
                "raw_text": "Họ và tên: Nguyễn Văn A\nNgày sinh: 15/06/2002\nSố CCCD: 079202001234",
                "extracted_fields": {
                    "full_name": "Nguyễn Văn A",
                    "dob": "2002-06-15",
                    "id_card_no": "079202001234",
                },
                "confidence": 1.0,
            }
        }
    }



class OCRErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "message": "File is not a valid PDF or corrupted.",
                "error_code": "INVALID_FILE_TYPE",
            }
        }
    }
