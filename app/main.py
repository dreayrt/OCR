import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.ocr_service import OCRService
from app.api.ocr import router as ocr_router
from app.api.health import router as health_router

# Thiết lập Logging tập trung
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ocr_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quản lý Lifecycle của ứng dụng (Stateless):
    - Nạp sẵn PaddleOCR Model vào memory một lần duy nhất lúc startup
    """
    logger.info("Application starting up (Stateless OCR Service)...")

    # Preload PaddleOCR singleton
    logger.info("Pre-warming PaddleOCR engine...")
    try:
        OCRService.get_instance()
        logger.info("PaddleOCR engine is ready.")
    except Exception as e:
        logger.warning(f"PaddleOCR preload deferred: {e}")

    yield

    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Independent OCR Service for single-page PDF processing with Direct Text Extraction & PaddleOCR Fallback.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handler tập trung: HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "An error occurred.")
        error_code = detail.get("error_code", "HTTP_ERROR")
    else:
        message = str(detail)
        error_code = f"HTTP_{exc.status_code}"

    logger.warning(f"HTTPException [{exc.status_code}] on {request.url.path}: {message} ({error_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": message,
            "error_code": error_code,
        },
    )


# Exception Handler tập trung: Mọi ngoại lệ chưa bắt được (ẩn stack trace)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error occurred while processing document.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


# Đăng ký Routers
app.include_router(health_router)
app.include_router(ocr_router)
