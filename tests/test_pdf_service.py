import fitz
import pytest
from app.services.pdf_service import PDFService


def create_in_memory_pdf_with_text(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_in_memory_blank_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_service_direct_text_extraction():
    sample_text = "Day la van ban tai lieu 1 trang co day du text layer de kiem tra trich xuat truc tiep."
    pdf_bytes = create_in_memory_pdf_with_text(sample_text)

    raw_text, img_np, is_ocr_needed = PDFService.inspect_and_extract_page(pdf_bytes)

    assert is_ocr_needed is False
    assert img_np is None
    assert "Day la van ban tai lieu 1 trang" in raw_text


def test_pdf_service_fallback_to_render_image():
    # PDF trang trắng không có text layer
    pdf_bytes = create_in_memory_blank_pdf()

    raw_text, img_np, is_ocr_needed = PDFService.inspect_and_extract_page(pdf_bytes)

    assert is_ocr_needed is True
    assert img_np is not None
    assert img_np.ndim == 3  # Kích thước H x W x 3
    assert raw_text == ""
