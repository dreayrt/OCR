# OCR Service (Stateless Single-Page PDF Processor)

Service độc lập chuyên xử lý OCR và trích xuất dữ liệu từ file **PDF 1 trang** (hợp đồng, hóa đơn, chứng từ...), hoạt động theo mô hình **Stateless Microservice** (không lưu database, không cần cấu hình DB) và trả về **JSON** chuẩn hóa ngay lập tức để hệ thống chính của bạn nhận dữ liệu và auto-fill vào form.

---

## 1. Tính Năng Chính

- **Stateless Microservice (Zero DB Overhead)**: Không cần cài đặt MySQL/PostgreSQL, không lưu dữ liệu tạm trên đĩa, tiết kiệm RAM tối đa, dễ dàng mở rộng theo chiều ngang (scale-out).
- **Xử lý Hybrid tối ưu**:
  - Ưu tiên trích xuất text trực tiếp từ text layer của PDF bằng **PyMuPDF** (siêu tốc ~50ms).
  - Tự động fallback sang **PaddleOCR** (tiếng Việt) khi phát hiện PDF scan (không có text layer hoặc text rỗng) ở độ phân giải **200 DPI**.
  - **Không dùng OpenCV custom preprocessing** (không denoise, không sharpen, không deskew làm nặng hệ thống).
- **Bộ nhớ tối ưu**: Xử lý PDF stream trực tiếp trong memory (RAM), trả kết quả JSON và tự động giải phóng.
- **PaddleOCR Singleton**: Nạp model 1 lần duy nhất khi container khởi động (pre-warm), tái sử dụng cho toàn bộ request.
- **Trích xuất có cấu trúc (Rule-based / Regex / Target Fields)**: Tự động trích xuất các trường thông tin (loại hợp đồng, số văn bản, ngày tháng, thời hạn, các bên liên quan, số tiền...). Cho phép truyền tham số `target_fields` để lọc chính xác các trường cần lấy.
- **Đóng gói Docker sẵn sàng tích hợp**: Hệ thống khác chỉ cần pull Docker image và gọi HTTP POST API.

---

## 📚 Tài Liệu Kỹ Thuật Chi Tiết
- [Tài liệu Hướng dẫn Sử dụng & Tích hợp API (HUONG_DAN_SU_DUNG.md)](docs/HUONG_DAN_SU_DUNG.md)
- [Tài liệu Kỹ thuật Chuyên sâu & Giải thích Mô hình Deep Learning (TAI_LIEU_KY_THUAT.md)](docs/TAI_LIEU_KY_THUAT.md)
- [Quy trình Kiểm thử Toàn diện End-to-End (TEST_FLOW.md)](docs/TEST_FLOW.md)

---

## 2. Kiến Trúc Luồng Hoạt Động (Stateless Flow)

```text
+-----------------------+           +-----------------------------+
|                       |           |                             |
|  HỆ THỐNG CỦA BẠN     |           |     OCR SERVICE (Stateless) |
|  (Frontend / Backend) |           |                             |
+-----------+-----------+           +--------------+--------------+
            |                                      |
            | 1. Upload PDF (POST /api/v1/ocr/pdf) |
            |------------------------------------->|
            |                                      | 2. Kiểm tra text layer (PyMuPDF)
            |                                      |    - Có text -> trích xuất trực tiếp
            |                                      |    - PDF scan -> PaddleOCR 200 DPI
            |                                      | 3. Bóc tách regex & target_fields
            |                                      |
            | 4. Trả về JSON Data (HTTP 200 OK)    |
            |<-------------------------------------|
            |                                      +------------------------------+
            | 5. Tự động fill vào form UI          (Không cần DB, giải phóng RAM)
            | 6. Người dùng duyệt & Submit         
            v                                      
    [(Database Hệ Thống Bạn)]
```

---

## 3. Cấu Trúc Dự Án

```text
ocr-service/
├── app/
│   ├── api/
│   │   ├── health.py             # Endpoint GET /health
│   │   └── ocr.py                # Endpoint POST /api/v1/ocr/pdf
│   ├── schemas/
│   │   └── document.py           # Pydantic Request/Response models & ProcessingStatus
│   ├── services/
│   │   ├── pdf_service.py        # Đọc text layer hoặc render 200 DPI
│   │   ├── ocr_service.py        # PaddleOCR Singleton engine
│   │   ├── extraction_service.py # Bóc tách regex & keyword matching
│   │   └── document_service.py   # Quản lý luồng xử lý Stateless
│   ├── utils/
│   │   ├── file_utils.py         # Quản lý UUID
│   │   └── validators.py         # Kiểm tra định dạng & dung lượng PDF
│   ├── config.py                 # Pydantic Settings đọc từ .env
│   └── main.py                   # Khởi tạo FastAPI app & Lifespan Pre-warm
├── tests/                        # Bộ kiểm thử tự động (pytest)
├── Dockerfile                    # Image Python 3.11-slim, tải sẵn model PaddleOCR
├── docker-compose.yml            # Khởi chạy OCR Service độc lập
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

---

## 4. Biến Môi Trường (Environment Variables)

Xem chi tiết trong file `.env.example`:

| Biến | Mặc định | Mô tả |
| :--- | :--- | :--- |
| `APP_NAME` | `OCR Service` | Tên ứng dụng |
| `APP_ENV` | `production` | Môi trường (`production` hoặc `development`) |
| `DEBUG` | `false` | Bật/tắt chế độ debug |
| `HOST` | `0.0.0.0` | Địa chỉ lắng nghe |
| `PORT` | `8000` | Cổng HTTP |
| `MAX_UPLOAD_SIZE_MB` | `10` | Kích thước file PDF tối đa (MB) |
| `OCR_LANGUAGE` | `vi` | Ngôn ngữ PaddleOCR (`vi`, `en`...) |
| `PDF_RENDER_DPI` | `200` | Độ phân giải render ảnh khi cần fallback OCR |
| `MIN_TEXT_LENGTH_THRESHOLD` | `20` | Ngưỡng ký tự tối thiểu để nhận diện text layer hợp lệ |

*(Lưu ý: Không cần cấu hình bất kỳ biến Database nào).*

---

## 5. Hướng Dẫn Chạy Cục Bộ (Local)

### 5.1. Cài đặt môi trường
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

### 5.2. Thiết lập file .env
```bash
cp .env.example .env
```

### 5.3. Chạy kiểm thử (Unit Tests)
```bash
pytest tests/ -v
```

### 5.4. Khởi chạy Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Truy cập tài liệu API Swagger tại: `http://localhost:8000/docs`

---

## 6. Hướng Dẫn Chạy Bằng Docker Compose (Khuyên dùng)

Chỉ cần chạy lệnh sau để khởi động OCR Service:

```bash
# Khởi động dịch vụ
docker compose up -d --build

# Kiểm tra log
docker compose logs -f ocr-service

# Dừng dịch vụ
docker compose down
```

---

## 7. Build & Chạy Container Riêng Lẻ

### 7.1. Build Docker Image
```bash
docker build -t ocr-service:latest .
```

### 7.2. Chạy Container độc lập
```bash
docker run -d \
  --name ocr-service \
  -p 8000:8000 \
  --env-file .env \
  ocr-service:latest
```

---

## 8. Tích Hợp API Dành Cho Hệ Thống Của Bạn

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

#### Gọi bằng cURL (Có thể kèm tham số lọc `target_fields`):
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/duong/dan/tai_lieu.pdf" \
  -F "target_fields=license_type,copyright_owner,distributor,contract_id,issue_date,expiry_date"
```

#### Gọi bằng Python:
```python
import requests

url = "http://localhost:8000/api/v1/ocr/pdf"
params = {
    "target_fields": "license_type,copyright_owner,distributor,contract_id,issue_date,expiry_date"
}

with open("contract.pdf", "rb") as f:
    files = {"file": ("contract.pdf", f, "application/pdf")}
    response = requests.post(url, files=files, data=params)
    data = response.json()
    
    # Bắt JSON kết quả và map vào form hệ thống
    if data.get("success"):
        extracted = data.get("extracted_fields", {})
        print("Trường trích xuất:", extracted)
        # Hệ thống của bạn auto-fill vào form tại đây!
```

#### Gọi bằng JavaScript (Node.js / Browser Frontend):
```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("target_fields", "license_type,copyright_owner,distributor,contract_id,issue_date,expiry_date");

const response = await fetch("http://localhost:8000/api/v1/ocr/pdf", {
  method: "POST",
  body: formData,
});

const result = await response.json();
if (result.success) {
  // Điền dữ liệu vào form người dùng
  document.getElementById("contractIdInput").value = result.extracted_fields.contract_id || "";
  document.getElementById("ownerInput").value = result.extracted_fields.copyright_owner || "";
}
```

**Response Thành Công (200 OK):**
```json
{
  "success": true,
  "document_uuid": "37f48e3a-e9fa-4541-b841-f63bbcb643eb",
  "processing_status": "COMPLETED",
  "ocr_engine": "direct_text",
  "confidence": 1.0,
  "raw_text": "...",
  "extracted_fields": {
    "license_type": "Hợp đồng chuyển nhượng quyền tác giả",
    "contract_id": "HD-2026/0889",
    "issue_date": "2026-10-15",
    "expiry_date": "2031-10-15",
    "copyright_owner": "NGUYỄN VĂN A",
    "distributor": "CÔNG TY PHÁT HÀNH XYZ"
  }
}
```
