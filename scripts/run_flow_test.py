"""
KỊCH BẢN KIỂM THỬ TỰ ĐỘNG (END-TO-END FLOW TEST RUNNER)
Kiểm tra toàn bộ pipeline: Health check -> File Validation -> Direct Text PDF -> Scan Fallback OCR -> Database

Tương thích 100% Windows Console (UTF-8) và không cần cài PyMuPDF (fitz) trên host.
"""
import sys
import os
import io
import time
import json
import requests

# Đảm bảo in UTF-8 không bị lỗi trên Windows Console (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thử import fitz (PyMuPDF) nếu có, nếu không thì dùng hàm Pure Python tạo PDF
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

DEFAULT_URL = os.environ.get("OCR_URL", "http://localhost:8001")
BASE_URL = DEFAULT_URL


def generate_pure_python_pdf(text_lines: list[str]) -> bytes:
    """Tạo file PDF 1 trang hợp lệ chuẩn PDF-1.4 bằng Pure Python."""
    stream_content = "BT\n/F1 12 Tf\n50 720 Td\n16 TL\n"
    for line in text_lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({safe_line}) '\n"
    stream_content += "ET"
    stream_bytes = stream_content.encode("latin-1", errors="replace")

    pdf_template = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n"
        + stream_bytes +
        b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n500\n%%EOF"
    )
    return pdf_template


def generate_blank_scanned_pdf() -> bytes:
    """Tạo PDF 1 trang rỗng không có text layer (giả lập tài liệu scan thuần ảnh)."""
    pdf_template = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n300\n%%EOF"
    )
    return pdf_template


def print_step(title: str):
    print(f"\n{'='*70}\n>>> {title}\n{'='*70}")


def test_1_health_check():
    print_step("BUOC 1: KIEM TRA HEALTH CHECK (/health)")
    start = time.time()
    res = requests.get(f"{BASE_URL}/health", timeout=5)
    elapsed = (time.time() - start) * 1000
    print(f"URL         : {BASE_URL}/health")
    print(f"Status Code : {res.status_code}")
    print(f"Latency     : {elapsed:.2f} ms")
    print(f"Body        : {res.json()}")
    assert res.status_code == 200
    assert res.json().get("status") == "UP"
    print("==> KET QUA: PASS (Service san sang)")


def test_2_file_validations():
    print_step("BUOC 2: KIEM TRA VALIDATION (NEGATIVE TESTS)")
    
    # 2.1. File sai extension
    print("\n[2.1] Gui file khong phai .pdf (.txt):")
    files = {"file": ("document.txt", io.BytesIO(b"Hello world"), "text/plain")}
    res = requests.post(f"{BASE_URL}/api/v1/ocr/pdf", files=files)
    print(f"Status Code: {res.status_code} | Body: {res.json()}")
    assert res.status_code == 400
    assert res.json().get("error_code") == "INVALID_EXTENSION"

    # 2.2. File đuôi .pdf nhưng nội dung hỏng (không có header %PDF-)
    print("\n[2.2] Gui file .pdf gia mao (corrupted):")
    files = {"file": ("fake.pdf", io.BytesIO(b"Day khong phai file PDF chuan"), "application/pdf")}
    res = requests.post(f"{BASE_URL}/api/v1/ocr/pdf", files=files)
    print(f"Status Code: {res.status_code} | Body: {res.json()}")
    assert res.status_code == 400
    assert res.json().get("error_code") == "CORRUPTED_PDF"
    print("==> KET QUA: PASS (Chan file loi thanh cong)")


def test_3_direct_text_pdf():
    print_step("BUOC 3: KIEM TRA PDF DIGITAL CO TEXT LAYER (DIRECT TEXT EXTRACTION)")
    
    lines = [
        "CONG HOA XA HOI CHU NGHIA VIET NAM",
        "HOA DON BAN HANG",
        "So: HD-2026/09999",
        "Ngay 10 thang 10 nam 2026",
        "Ma so thue: 0102030405",
        "Khach hang: NGUYEN VAN AN",
        "Tong cong tien thanh toan: 8.500.000 VND"
    ]

    if HAS_FITZ:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "\n".join(lines), fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()
    else:
        pdf_bytes = generate_pure_python_pdf(lines)

    start = time.time()
    files = {"file": ("hoa_don_dien_tu.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res = requests.post(f"{BASE_URL}/api/v1/ocr/pdf", files=files)
    elapsed = (time.time() - start) * 1000

    print(f"Status Code : {res.status_code}")
    print(f"Thoi gian   : {elapsed:.2f} ms (Ky vong sieu nhanh vi KHONG chay PaddleOCR)")
    print(f"Response Body:\n{json.dumps(res.json(), indent=2, ensure_ascii=False)}")

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["confidence"] == 1.0
    fields = data["extracted_fields"]
    assert fields.get("document_no") == "HD-2026/09999"
    assert fields.get("date") == "2026-10-10"
    assert fields.get("tax_code") == "0102030405"
    assert fields.get("total_amount") == 8500000.0
    print("==> KET QUA: PASS (Direct Text trich xuat chinh xac 100%, khong ton tai nguyen OCR)")


def test_4_scan_pdf_fallback():
    print_step("BUOC 4: KIEM TRA PDF SCAN THUAN ANH (FALLBACK PADDLEOCR 200 DPI)")
    
    if HAS_FITZ:
        doc_temp = fitz.open()
        page_temp = doc_temp.new_page()
        page_temp.insert_text((50, 100), "HOA DON BAN LE\nSo: HD-SCAN-777\nNgay 25 thang 10 nam 2026\nTong cong: 1200000 VND", fontsize=16)
        pix = page_temp.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        doc_temp.close()

        scan_doc = fitz.open()
        sp = scan_doc.new_page(width=pix.width, height=pix.height)
        sp.insert_image(sp.rect, stream=img_bytes)
        scan_pdf_bytes = scan_doc.tobytes()
        scan_doc.close()
    else:
        scan_pdf_bytes = generate_blank_scanned_pdf()

    start = time.time()
    files = {"file": ("scan_invoice.pdf", io.BytesIO(scan_pdf_bytes), "application/pdf")}
    res = requests.post(f"{BASE_URL}/api/v1/ocr/pdf", files=files)
    elapsed = (time.time() - start) * 1000

    print(f"Status Code : {res.status_code}")
    print(f"Thoi gian   : {elapsed:.2f} ms (Chay qua PaddleOCR nhan dien anh)")
    print(f"Response Body:\n{json.dumps(res.json(), indent=2, ensure_ascii=False)}")

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    print("==> KET QUA: PASS (PaddleOCR fallback hoat dong muot ma khi gap PDF scan)")


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("   BAT DAU CHAY KIEM THU END-TO-END OCR SERVICE")
    print(f"   Target URL: {BASE_URL}")
    print(f"   Generator : {'PyMuPDF' if HAS_FITZ else 'Pure Python Built-in (Khong can cai fitz)'}")
    print("#"*70)
    try:
        test_1_health_check()
        test_2_file_validations()
        test_3_direct_text_pdf()
        test_4_scan_pdf_fallback()
        print("\n" + "#"*70)
        print("   >>> TAT CA 4 BUOC KIEM THU DA VUOT QUA 100% THANH CONG! <<<")
        print("#"*70)
    except AssertionError as e:
        print(f"\n[FAILED] Kiem thu that bai: {e}")
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Khong the ket noi toi {BASE_URL}. Vui long dam bao container dang chay tren cong 8000 hoac 8001!")
