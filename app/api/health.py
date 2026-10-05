from fastapi import APIRouter
from app.schemas.document import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Kiểm tra trạng thái hoạt động của OCR Service container.",
)
async def health_check():
    return {"status": "UP"}
