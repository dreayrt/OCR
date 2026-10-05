from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "UP"


class FieldDetail(BaseModel):
    value: Any
    confidence: float = 1.0


class OCRSuccessResponse(BaseModel):
    success: bool = True
    document_uuid: str
    processing_status: str
    extracted_fields: Dict[str, Any]
    confidence: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "document_uuid": "c3a52753-8a57-4d55-aae1-1e525de7bd87",
                "processing_status": "COMPLETED",
                "extracted_fields": {
                    "document_no": "HD-2026/001",
                    "date": "2026-10-05",
                    "total_amount": 1250000.0,
                    "tax_code": "0102030405",
                },
                "confidence": 0.98,
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
