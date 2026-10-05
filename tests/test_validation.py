import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_invalid_extension():
    # File txt giả lập
    files = {"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")}
    response = client.post("/api/v1/ocr/pdf", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "INVALID_EXTENSION"


def test_upload_corrupted_pdf():
    # File đuôi .pdf nhưng nội dung không phải header PDF
    files = {"file": ("fake.pdf", io.BytesIO(b"Not a real pdf content"), "application/pdf")}
    response = client.post("/api/v1/ocr/pdf", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "CORRUPTED_PDF"
