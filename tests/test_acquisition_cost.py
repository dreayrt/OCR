import io

import fitz
from PIL import Image

from app.services.extraction_service import ExtractionService
from app.services.pdf_service import PDFService


def test_song_rights_cost_requires_explicit_label_and_currency():
    text = "Chi phí mua quyền bài hát: 1.500.000 VND\nTổng tiền thanh toán: 3.000.000 VNĐ"
    value = ExtractionService.extract_acquisition_cost(text)
    assert value["amount_vnd"] == 1_500_000
    assert "Chi phí mua quyền" in value["source_text"]
    assert ExtractionService.extract_acquisition_cost("Tổng tiền thanh toán: 3.000.000 VNĐ") == {}


def test_song_rights_cost_marks_ambiguous_contract_unknown():
    text = "Chi phí mua quyền: 1.000.000 VND\nGiá mua bản quyền: 2.000.000 VND"
    assert ExtractionService.extract_acquisition_cost(text) == {}


def test_cost_accepts_unaccented_ocr_label():
    result = ExtractionService.extract_acquisition_cost("Chi phi mua quyen bai hat: 1,5 trieu VND")
    assert result["amount_vnd"] == 1_500_000


def test_cost_accepts_contract_label_chi_phi_ban_quyen():
    for label in ("Chi phi ban quyen", "Chi phí bản quyền"):
        fields, _ = ExtractionService.extract_fields(f"{label}: 15.000.000 VND")
        assert fields["acquisition_cost_vnd"] == 15_000_000


def test_cost_on_second_pdf_page_is_available_for_extraction():
    document = fitz.open()
    document.new_page().insert_text((40, 80), "License agreement terms and artist identification")
    document.new_page().insert_text((40, 80), "License acquisition cost: 1500000 VND. This signed agreement is for a single song.")
    pages = list(PDFService.inspect_and_extract_pages(document.tobytes()))
    document.close()
    assert len(pages) == 2
    combined = "\n".join(f"--- PAGE {number} ---\n{text}" for number, text, _ in pages)
    result = ExtractionService.extract_acquisition_cost(combined)
    assert result["amount_vnd"] == 1_500_000
    assert result["page"] == 2


def test_pdf_page_with_text_and_embedded_image_is_sent_to_ocr():
    image = Image.new("RGB", (60, 20), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((40, 80), "This is enough searchable contract text for native extraction.")
    page.insert_image(fitz.Rect(40, 100, 100, 120), stream=buffer.getvalue())
    page_number, text, image_array = next(PDFService.inspect_and_extract_pages(document.tobytes()))
    document.close()
    assert page_number == 1
    assert "searchable contract text" in text
    assert image_array is not None


