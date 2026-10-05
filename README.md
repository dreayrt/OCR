# OCR Service (Standalone Single-Page PDF Processor)

Service độc lập chuyên xử lý OCR và trích xuất dữ liệu từ file **PDF 1 trang** (hóa đơn, văn bản, chứng từ...), lưu trữ kết quả xuống **MySQL** và trả về **JSON** chuẩn hóa qua REST API.

---

## 1. Tính Năng Chính

- **Xử lý Hybrid tối ưu**:
  - Ưu tiên trích xuất text trực tiếp từ text layer của PDF bằng **PyMuPDF**.
  - Tự động fallback sang **PaddleOCR** (tiếng Việt) khi phát hiện PDF scan (không có text layer hoặc text rỗng) ở độ phân giải **200 DPI**.
  - **Không dùng OpenCV custom preprocessing** (không denoise, không sharpen, không deskew làm nặng hệ thống).
- **Bộ nhớ tối ưu**: Xử lý PDF stream trực tiếp trong memory, không ghi file rác xuống disk.
- **PaddleOCR Singleton**: Nạp model 1 lần duy nhất khi container khởi động (pre-warm), tái sử dụng cho toàn bộ request.
- **Trích xuất có cấu trúc (Rule-based / Regex)**: Tự động bóc tách số hóa đơn, ngày tháng, mã số thuế, tổng tiền, người mua...
- **Database Transaction an toàn**: Tự động rollback nếu xảy ra lỗi trong quá trình lưu dữ liệu vào `documents` và `document_fields`.
- **Đóng gói Docker sẵn sàng tích hợp**: Hệ thống khác chỉ cần pull Docker image và gọi HTTP POST API.

---

## 📚 Tài Liệu Kỹ Thuật Chi Tiết
- [Tài liệu Hướng dẫn Sử dụng & Tích hợp API (HUONG_DAN_SU_DUNG.md)](docs/HUONG_DAN_SU_DUNG.md)
- [Tài liệu Kỹ thuật Chuyên sâu & Giải thích Mô hình Deep Learning (TAI_LIEU_KY_THUAT.md)](docs/TAI_LIEU_KY_THUAT.md)
- [Quy trình Kiểm thử Toàn diện End-to-End (TEST_FLOW.md)](docs/TEST_FLOW.md)

---

## 2. Cấu Trúc Dự Án

```text
ocr-service/
├── app/
│   ├── api/
│   │   ├── health.py             # Endpoint GET /health
│   │   └── ocr.py                # Endpoint POST /api/v1/ocr/pdf
│   ├── database/
│   │   └── database.py           # Kết nối SQLAlchemy Session & Init DB
│   ├── models/
│   │   └── document.py           # Bảng documents & document_fields
│   ├── schemas/
│   │   └── document.py           # Pydantic Request/Response models
│   ├── services/
│   │   ├── pdf_service.py        # Đọc text layer hoặc render 200 DPI
│   │   ├── ocr_service.py        # PaddleOCR Singleton engine
│   │   ├── extraction_service.py # Bóc tách regex & keyword matching
│   │   └── document_service.py   # Quản lý flow và Transaction DB
│   ├── utils/
│   │   ├── file_utils.py         # Quản lý UUID
│   │   └── validators.py         # Kiểm tra định dạng & dung lượng PDF
│   ├── config.py                 # Pydantic Settings đọc từ .env
│   └── main.py                   # Khởi tạo FastAPI app & Lifespan
├── tests/                        # Bộ kiểm thử tự động (pytest)
├── Dockerfile                    # Image Python 3.11-slim, tải sẵn model PaddleOCR
├── docker-compose.yml            # Điều phối OCR Service và MySQL Database
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

---

## 3. Biến Môi Trường (Environment Variables)

Xem chi tiết trong file `.env.example`:

| Biến | Mặc định | Mô tả |
| :--- | :--- | :--- |
| `DB_HOST` | `mysql` | Host kết nối MySQL (dùng tên container khi chạy Compose) |
| `DB_PORT` | `3306` | Cổng MySQL |
| `DB_NAME` | `ocr_db` | Tên cơ sở dữ liệu |
| `DB_USER` | `ocr_user` | Tài khoản MySQL |
| `DB_PASSWORD` | `ocr_password_secure_123` | Mật khẩu MySQL |
| `MAX_UPLOAD_SIZE_MB` | `10` | Kích thước file PDF tối đa (MB) |
| `OCR_LANGUAGE` | `vi` | Ngôn ngữ PaddleOCR (`vi`, `en`...) |
| `PDF_RENDER_DPI` | `200` | Độ phân giải render ảnh khi cần fallback OCR |
| `MIN_TEXT_LENGTH_THRESHOLD` | `20` | Ngưỡng ký tự tối thiểu để nhận diện text layer hợp lệ |

---

## 4. Hướng Dẫn Chạy Cục Bộ (Local)

### 4.1. Cài đặt môi trường
Yêu cầu Python 3.10 hoặc 3.11:

```bash
# Tạo môi trường ảo
python -m venv .venv
# Kích hoạt trên Windows
.venv\Scripts\activate
# Hoặc trên Linux/macOS
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 4.2. Thiết lập file .env
```bash
cp .env.example .env
```

### 4.3. Chạy kiểm thử (Unit Tests)
```bash
pytest tests/ -v
```

### 4.4. Khởi chạy Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Truy cập tài liệu API Swagger tại: `http://localhost:8000/docs`

---

## 5. Hướng Dẫn Chạy Bằng Docker Compose (Khuyên dùng)

Khởi chạy đồng thời cả **OCR Service** và cơ sở dữ liệu **MySQL**:

```bash
# Khởi động dịch vụ
docker compose up -d --build

# Kiểm tra log
docker compose logs -f ocr-service

# Dừng dịch vụ
docker compose down
```

---

## 6. Build & Chạy Container Riêng Lẻ

### 6.1. Build Docker Image
```bash
docker build -t ocr-service:latest .
```

Kiểm tra image đã build thành công:
```bash
docker images | grep ocr-service
```

### 6.2. Chạy Container độc lập
```bash
docker run -d \
  --name ocr-service \
  -p 8000:8000 \
  --env-file .env \
  ocr-service:latest
```

---

## 7. Push & Pull Image Lên Docker Registry

### 7.1. Đẩy Image lên Registry
```bash
# Đổi tag image theo registry của bạn
docker tag ocr-service:latest <your-registry>/ocr-service:latest

# Đăng nhập registry
docker login <your-registry>

# Push image
docker push <your-registry>/ocr-service:latest
```

### 7.2. Hệ thống khác Pull và Chạy
Hệ thống backend khác không cần cài đặt Python hay thư viện OCR, chỉ cần chạy container:

```bash
docker pull <your-registry>/ocr-service:latest

docker run -d \
  --name ocr-service \
  -p 8000:8000 \
  -e DB_HOST=your-mysql-host \
  -e DB_USER=your-user \
  -e DB_PASSWORD=your-password \
  -e DB_NAME=ocr_db \
  <your-registry>/ocr-service:latest
```

---

## 8. Tích Hợp API Dành Cho Backend Khác

### 8.1. Kiểm tra trạng thái (Health Check)
```bash
curl -X GET http://localhost:8000/health
```
**Response:**
```json
{
  "status": "UP"
}
```

### 8.2. Gửi PDF để OCR và Trích Xuất Dữ Liệu
Endpoint: `POST /api/v1/ocr/pdf` (multipart/form-data)

#### Gọi bằng cURL:
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/duong/dan/tai_lieu.pdf"
```

#### Gọi bằng Python:
```python
import requests

url = "http://localhost:8000/api/v1/ocr/pdf"
with open("invoice.pdf", "rb") as f:
    files = {"file": ("invoice.pdf", f, "application/pdf")}
    response = requests.post(url, files=files)
    print(response.json())
```

**Response Thành Công (200 OK):**
```json
{
  "success": true,
  "document_uuid": "37f48e3a-e9fa-4541-b841-f63bbcb643eb",
  "processing_status": "COMPLETED",
  "extracted_fields": {
    "title": "HÓA ĐƠN BÁN HÀNG",
    "document_no": "HD-2026/0889",
    "date": "2026-10-15",
    "tax_code": "0108999888",
    "total_amount": 1500000.0,
    "customer_name": "NGUYỄN VĂN A"
  },
  "confidence": 1.0
}
```

**Response Khi Có Lỗi (400 / 413 / 500):**
```json
{
  "success": false,
  "message": "Only .pdf files are allowed.",
  "error_code": "INVALID_EXTENSION"
}
```
