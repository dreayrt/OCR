import re
import logging
from typing import Dict, Any, Tuple
from app.utils.validators import clean_text

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Trích xuất dữ liệu có cấu trúc từ raw text bằng Regex, Keyword Matching & Rule-based.
    Tuyệt đối không sử dụng LLM hay NLP model ngoài.
    """

    @classmethod
    def extract_fields(cls, raw_text: str, base_confidence: float = 1.0) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Phân tích raw text và trích xuất các trường thông tin chuẩn:
        - document_no (Số hóa đơn / Số văn bản / Mã chứng từ)
        - date (Ngày tháng phát hành, chuẩn hóa YYYY-MM-DD)
        - tax_code (Mã số thuế 10 hoặc 13 số)
        - total_amount (Tổng tiền thanh toán - kiểu số float)
        - customer_name (Đơn vị mua hàng / Người nhận)
        - title (Tiêu đề tài liệu)

        Returns:
            Tuple[extracted_fields_dict, field_confidences_dict]
        """
        text = clean_text(raw_text)
        fields: Dict[str, Any] = {}
        confidences: Dict[str, float] = {}

        if not text:
            return fields, confidences

        # 1. Trích xuất tiêu đề (Title)
        title = cls._extract_title(text)
        if title:
            fields["title"] = title
            confidences["title"] = base_confidence

        # 2. Trích xuất Số văn bản / Số hóa đơn (document_no)
        doc_no = cls._extract_document_no(text)
        if doc_no:
            fields["document_no"] = doc_no
            confidences["document_no"] = base_confidence

        # 3. Trích xuất Ngày tháng (date)
        doc_date = cls._extract_date(text)
        if doc_date:
            fields["date"] = doc_date
            confidences["date"] = base_confidence

        # 4. Trích xuất Mã số thuế (tax_code)
        tax_code = cls._extract_tax_code(text)
        if tax_code:
            fields["tax_code"] = tax_code
            confidences["tax_code"] = base_confidence

        # 5. Trích xuất Tổng tiền (total_amount)
        total_amount = cls._extract_total_amount(text)
        if total_amount is not None:
            fields["total_amount"] = total_amount
            confidences["total_amount"] = base_confidence

        # 6. Trích xuất Tên khách hàng / Người mua (customer_name)
        customer = cls._extract_customer_name(text)
        if customer:
            fields["customer_name"] = customer
            confidences["customer_name"] = round(base_confidence * 0.9, 2)

        logger.info(f"Extraction completed: {len(fields)} fields identified.")
        return fields, confidences

    @staticmethod
    def _extract_title(text: str) -> str:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            upper_line = line.upper()
            if any(k in upper_line for k in ["HÓA ĐƠN", "HOA DON", "GIẤY ĐỀ NGHỊ", "BIÊN BẢN", "THÔNG BÁO", "PHIẾU", "INVOICE", "RECEIPT"]):
                return line
        return lines[0] if lines else "TÀI LIỆU"

    @staticmethod
    def _extract_document_no(text: str) -> str:
        # Tìm các mẫu số hóa đơn/văn bản: "Số: ...", "HĐ số:", "No.:", "Invoice No:"
        patterns = [
            r"(?:Số|So|HĐ\s*số|Mã\s*số|Invoice\s*No|No\.?)\s*[:.]?\s*([A-Za-z0-9\/\-_]{3,25})",
            r"(?:Ký\s*hiệu|Ký\s*hiệu\s*mẫu\s*số)\s*[:.]?\s*([A-Za-z0-9\/\-_]{3,20})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if not val.lower().startswith("thuế"):
                    return val
        return ""

    @staticmethod
    def _extract_date(text: str) -> str:
        # Mẫu 1: "Ngày 05 tháng 10 năm 2026" hoặc "Ngay 05 thang 10 nam 2026"
        m1 = re.search(r"(?:ngày|ngay)\s*(\d{1,2})\s*(?:tháng|thang)\s*(\d{1,2})\s*(?:năm|nam)\s*(\d{4})", text, re.IGNORECASE)
        if m1:
            d, m, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
            return f"{y:04d}-{m:02d}-{d:02d}"

        # Mẫu 2: DD/MM/YYYY hoặc DD-MM-YYYY
        m2 = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b", text)
        if m2:
            d, m, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            if 1 <= d <= 31 and 1 <= m <= 12:
                return f"{y:04d}-{m:02d}-{d:02d}"

        # Mẫu 3: YYYY-MM-DD
        m3 = re.search(r"\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b", text)
        if m3:
            y, m, d = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
            if 1 <= d <= 31 and 1 <= m <= 12:
                return f"{y:04d}-{m:02d}-{d:02d}"

        return ""

    @staticmethod
    def _extract_tax_code(text: str) -> str:
        # Mã số thuế: 10 chữ số hoặc 13 chữ số (hỗ trợ có dấu và không dấu)
        patterns = [
            r"(?:Mã\s*số\s*thuế|Ma\s*so\s*thue|MST|Tax\s*Code)\s*[:.]?\s*([0-9]{10}(?:-[0-9]{3})?)",
            r"\b([0-9]{10}-[0-9]{3})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_total_amount(text: str) -> Any:
        patterns = [
            r"(?:Tổng\s*cộng\s*tiền\s*thanh\s*toán|Tong\s*cong\s*tien\s*thanh\s*toan|Tổng\s*tiền\s*thanh\s*toán|Tong\s*tien\s*thanh\s*toan|Tổng\s*cộng|Tong\s*cong|Thành\s*tiền|Thanh\s*tien|Total\s*Amount)\s*[:.]?\s*([0-9\.,\s]+)(?:VNĐ|VND|đ|\$)?",
            r"(?:Số\s*tiền\s*bằng\s*số|So\s*tien\s*bang\s*so)\s*[:.]?\s*([0-9\.,\s]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_num = match.group(1).strip()
                clean_num = re.sub(r"[^\d\.,]", "", raw_num)
                if clean_num:
                    try:
                        if "." in clean_num and "," in clean_num:
                            clean_num = clean_num.replace(".", "").replace(",", ".")
                        elif "." in clean_num and len(clean_num.split(".")[-1]) == 3:
                            clean_num = clean_num.replace(".", "")
                        elif "," in clean_num and len(clean_num.split(",")[-1]) == 3:
                            clean_num = clean_num.replace(",", "")
                        elif "," in clean_num:
                            clean_num = clean_num.replace(",", ".")
                        return float(clean_num)
                    except ValueError:
                        continue
        return None

    @staticmethod
    def _extract_customer_name(text: str) -> str:
        patterns = [
            r"(?:Tên\s*khách\s*hàng|Ten\s*khach\s*hang|Họ\s*tên\s*người\s*mua|Ho\s*ten\s*nguoi\s*mua|Người\s*mua\s*hàng|Nguoi\s*mua\s*hang|Khách\s*hàng|Khach\s*hang|Buyer)\s*[:.]?\s*([^\n\r,]+)",
            r"(?:Đơn\s*vị\s*mua\s*hàng|Don\s*vi\s*mua\s*hang)\s*[:.]?\s*([^\n\r,]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if len(val) > 2 and not val.lower().startswith("mã số") and not val.lower().startswith("ma so"):
                    return val
        return ""
