import io
import fitz
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_pipeline_direct_text_pdf():
    # 1. Tạo PDF 1 trang mẫu hóa đơn có text layer
    doc = fitz.open()
    page = doc.new_page()
    content = """
    CONG HOA XA HOI CHU NGHIA VIET NAM
    HOA DON BAN HANG
    So: HD-2026/9999
    Ngay 18 thang 10 nam 2026
    Ma so thue: 0109998888
    Khach hang: CONG TY ABC
    Tong cong tien thanh toan: 2.500.000 VND
    """
    page.insert_text((50, 72), content, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()

    # 2. Gửi request POST /api/v1/ocr/pdf
    files = {"file": ("test_invoice.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/ocr/pdf", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["processing_status"] == "COMPLETED"
    assert "document_uuid" in data
    assert data["confidence"] == 1.0

    # Kiểm tra các trường đã được trích xuất
    fields = data["extracted_fields"]
    assert fields["document_no"] == "HD-2026/9999"
    assert fields["date"] == "2026-10-18"
    assert fields["tax_code"] == "0109998888"
    assert fields["total_amount"] == 2500000.0
    assert "CONG TY ABC" in fields["customer_name"]
