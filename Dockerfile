FROM python:3.11-slim

# Thiết lập biến môi trường chuẩn hóa cho container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    FLAGS_use_mkldnn=0 \
    FLAGS_use_xdnn=0 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

# Cài đặt thư viện hệ thống C/C++ cần thiết cho PyMuPDF và PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Tận dụng Docker layer caching: copy requirements trước
COPY requirements.txt .

# Cài đặt Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy toàn bộ mã nguồn ứng dụng
COPY app/ ./app/

# Expose port mặc định của FastAPI
EXPOSE 8000

# Khởi chạy Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
