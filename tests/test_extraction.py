import pytest
from app.services.extraction_service import ExtractionService


def test_extraction_invoice_fields():
    sample_text = """
    CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
    Độc lập - Tự do - Hạnh phúc

    HÓA ĐƠN BÁN HÀNG
    Số: HD-2026/0889
    Ngày 15 tháng 10 năm 2026

    Đơn vị bán hàng: CÔNG TY TNHH CÔNG NGHỆ OCR
    Mã số thuế: 0108999888

    Khách hàng: NGUYỄN VĂN A
    Tổng cộng tiền thanh toán: 1.500.000 VNĐ
    """

    fields, confidences = ExtractionService.extract_fields(sample_text)

    assert fields["document_no"] == "HD-2026/0889"
    assert fields["date"] == "2026-10-15"
    assert fields["tax_code"] == "0108999888"
    assert fields["total_amount"] == 1500000.0
    assert "HÓA ĐƠN BÁN HÀNG" in fields["title"]
    assert "NGUYỄN VĂN A" in fields["customer_name"]
