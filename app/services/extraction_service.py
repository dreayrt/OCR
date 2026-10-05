import re
import logging
from typing import Dict, Any, Tuple
from app.utils.validators import clean_text

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Trích xuất dữ liệu có cấu trúc từ raw text bằng Regex, Keyword Matching & Rule-based.
    Hỗ trợ:
    - Hóa đơn / Chứng từ tài chính (document_no, tax_code, total_amount, date, customer_name, title)
    - Thông tin cá nhân / Giấy tờ hồ sơ (full_name, dob, id_card_no, address, email, phone_number)
    - Cơ chế Dynamic Key-Value Parsing cho các cặp 'Nhãn: Giá trị' trong tài liệu
    """

    @classmethod
    def extract_fields(cls, raw_text: str, base_confidence: float = 1.0) -> Tuple[Dict[str, Any], Dict[str, float]]:
        text = clean_text(raw_text)
        fields: Dict[str, Any] = {}
        confidences: Dict[str, float] = {}

        if not text:
            return fields, confidences

        # --- A. TRÍCH XUẤT THÔNG TIN CÁ NHÂN / HỒ SƠ ---
        # 1. Họ và tên (full_name)
        full_name = cls._extract_full_name(text)
        if full_name:
            fields["full_name"] = full_name
            confidences["full_name"] = base_confidence

        # 2. Ngày sinh (dob)
        dob = cls._extract_dob(text)
        if dob:
            fields["dob"] = dob
            confidences["dob"] = base_confidence

        # 3. Số CCCD / CMND (id_card_no)
        id_card = cls._extract_id_card_no(text)
        if id_card:
            fields["id_card_no"] = id_card
            confidences["id_card_no"] = base_confidence

        # 4. Địa chỉ (address)
        address = cls._extract_address(text)
        if address:
            fields["address"] = address
            confidences["address"] = round(base_confidence * 0.95, 2)

        # 5. Email
        email = cls._extract_email(text)
        if email:
            fields["email"] = email
            confidences["email"] = base_confidence

        # 6. Số điện thoại (phone_number)
        phone = cls._extract_phone_number(text)
        if phone:
            fields["phone_number"] = phone
            confidences["phone_number"] = base_confidence

        # --- B. TRÍCH XUẤT BẢN QUYỀN & GIẤY PHÉP BÀI HÁT (SONG LICENSES) ---
        # 7. Loại bản quyền / Giấy phép (license_type)
        lic_type = cls._extract_license_type(text)
        if lic_type:
            fields["license_type"] = lic_type
            confidences["license_type"] = base_confidence

        # 8. Chủ sở hữu quyền tác giả (copyright_owner)
        owner = cls._extract_copyright_owner(text)
        if owner:
            fields["copyright_owner"] = owner
            confidences["copyright_owner"] = base_confidence

        # 9. Đơn vị phân phối (distributor / distributor_name)
        distributor = cls._extract_distributor(text)
        if distributor:
            fields["distributor"] = distributor
            confidences["distributor"] = base_confidence

        # 10. Mã hợp đồng (contract_id)
        contract_id = cls._extract_contract_id(text)
        if contract_id:
            fields["contract_id"] = contract_id
            confidences["contract_id"] = base_confidence

        # 11. Ngày cấp / Bắt đầu (issue_date)
        issue_d = cls._extract_issue_date(text)
        if issue_d:
            fields["issue_date"] = issue_d
            confidences["issue_date"] = base_confidence

        # 12. Ngày hết hạn (expiry_date)
        expiry_d = cls._extract_expiry_date(text)
        if expiry_d:
            fields["expiry_date"] = expiry_d
            confidences["expiry_date"] = base_confidence

        # --- C. TRÍCH XUẤT HÓA ĐƠN / TÀI LIỆU CHỨNG TỪ ---
        # 13. Tiêu đề (Title)
        title = cls._extract_title(text)
        if title:
            fields["title"] = title
            confidences["title"] = base_confidence

        # 14. Số văn bản / Số hóa đơn (document_no) - Không bắt nhầm CCCD / SĐT / HĐ
        doc_no = cls._extract_document_no(text)
        if doc_no and not contract_id:
            fields["document_no"] = doc_no
            confidences["document_no"] = base_confidence

        # 15. Ngày tháng phát hành văn bản (date) - Loại trừ ngày sinh và ngày cấp HĐ
        doc_date = cls._extract_date(text)
        if doc_date and not issue_d:
            fields["date"] = doc_date
            confidences["date"] = base_confidence

        # 16. Mã số thuế (tax_code)
        tax_code = cls._extract_tax_code(text)
        if tax_code:
            fields["tax_code"] = tax_code
            confidences["tax_code"] = base_confidence

        # 17. Tổng tiền (total_amount)
        total_amount = cls._extract_total_amount(text)
        if total_amount is not None:
            fields["total_amount"] = total_amount
            confidences["total_amount"] = base_confidence

        # 18. Tên khách hàng / Người mua (customer_name)
        customer = cls._extract_customer_name(text)
        if customer and not full_name and not owner:
            fields["customer_name"] = customer
            confidences["customer_name"] = round(base_confidence * 0.9, 2)

        # --- D. TRÍCH XUẤT DYNAMIC KEY-VALUE CHO CÁC DÒNG CÒN LẠI ---
        cls._extract_dynamic_pairs(text, fields, confidences, base_confidence)

        logger.info(f"Extraction completed: {len(fields)} fields identified.")
        return fields, confidences


    @staticmethod
    def _extract_full_name(text: str) -> str:
        patterns = [
            r"(?:Họ\s*và\s*tên|Họ\s*tên|Ho\s*va\s*ten|Ho\s*ten|Full\s*Name|Name)\s*[:.]?\s*([^\n\r,;]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if len(val) >= 2:
                    return val
        return ""

    @classmethod
    def _extract_dob(cls, text: str) -> str:
        patterns = [
            r"(?:Ngày\s*sinh|Ngay\s*sinh|Sinh\s*ngày|Date\s*of\s*birth|DOB)\s*[:.]?\s*([^\n\r]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                raw_dob = m.group(1).strip()
                parsed = cls._parse_date_string(raw_dob)
                return parsed if parsed else raw_dob
        return ""

    @staticmethod
    def _extract_id_card_no(text: str) -> str:
        patterns = [
            r"(?:Số\s*CCCD|So\s*CCCD|Số\s*CMND|So\s*CMND|Số\s*định\s*danh|Số\s*căn\s*cước|CCCD|CMND|ID\s*Card|Identity\s*No)\s*[:.]?\s*([0-9]{9,12})",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _extract_address(text: str) -> str:
        patterns = [
            r"(?:Địa\s*chỉ|Dia\s*chi|Nơi\s*thường\s*trú|Noi\s*thuong\s*tru|Nơi\s*ở\s*hiện\s*tại|Address)\s*[:.]?\s*([^\n\r]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if len(val) >= 3:
                    return val
        return ""

    @staticmethod
    def _extract_email(text: str) -> str:
        # Ưu tiên mẫu có nhãn Email:
        m = re.search(r"(?:Email|E-mail|Thư\s*điện\s*tử)\s*[:.]?\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Fallback tìm địa chỉ email bất kỳ
        m2 = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", text)
        if m2:
            return m2.group(0).strip()
        return ""

    @staticmethod
    def _extract_phone_number(text: str) -> str:
        patterns = [
            r"(?:Số\s*điện\s*thoại|So\s*dien\s*thoai|Điện\s*thoại|Dien\s*thoai|Hotline|Phone|Tel|Mobile)\s*[:.]?\s*([0-9\+\-\.\s]{9,16})",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                clean = re.sub(r"[^\d+]", "", raw)
                if len(clean) >= 9:
                    return clean

        # Mẫu số di động Việt Nam (03, 05, 07, 08, 09) hoặc +84
        vn = re.search(r"\b((?:\+?84|0)(?:3|5|7|8|9)\d{8})\b", text)
        if vn:
            return vn.group(1)
        return ""

    # ==========================================
    # CÁC HÀM TRÍCH XUẤT CHO BẢN QUYỀN BÀI HÁT (SONG LICENSES)
    # ==========================================

    @staticmethod
    def _extract_license_type(text: str) -> str:
        """
        Trích xuất loại bản quyền / giấy phép:
        DIGITAL_STREAMING, EXCLUSIVE, NON_EXCLUSIVE, MASTER_USE, SYNC, MECHANICAL...
        """
        # Mẫu có nhãn rõ ràng
        patterns = [
            r"(?:Loại\s*bản\s*quyền\s*\/?\s*giấy\s*phép|Loại\s*giấy\s*phép|Loại\s*bản\s*quyền|Hình\s*thức\s*cấp\s*phép|License\s*Type)\s*[:.]?\s*([^\n\r]+)",
        ]
        raw_val = ""
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                raw_val = m.group(1).strip()
                break

        search_corpus = f"{raw_val} {text}".lower()

        if any(k in search_corpus for k in ["digital_streaming", "digital streaming", "phát trực tuyến", "nhạc số", "streaming"]):
            return "DIGITAL_STREAMING"
        if any(k in search_corpus for k in ["non_exclusive", "non-exclusive", "không độc quyền"]):
            return "NON_EXCLUSIVE"
        if any(k in search_corpus for k in ["exclusive", "độc quyền", "toàn quyền"]):
            return "EXCLUSIVE"
        if any(k in search_corpus for k in ["master_use", "master use", "quyền bản ghi", "bản ghi âm"]):
            return "MASTER_USE"
        if any(k in search_corpus for k in ["sync", "đồng bộ", "synchronization"]):
            return "SYNC"
        if any(k in search_corpus for k in ["mechanical", "tái sản xuất", "sao chép"]):
            return "MECHANICAL"

        return raw_val if raw_val else ""

    @staticmethod
    def _extract_copyright_owner(text: str) -> str:
        """Trích xuất Chủ sở hữu quyền tác giả (copyright_owner)"""
        patterns = [
            r"(?:Chủ\s*sở\s*hữu\s*(?:quyền\s*tác\s*giả|bản\s*quyền)?|Chu\s*so\s*huu\s*(?:quyen\s*tac\s*gia|ban\s*quyen)?|Ch[·\.\s]*s[·\.\s]*h[·\.\s]*u(?:\s*quy[·\.\s]*n\s*t[áa]c\s*gi[·\.\s]*)?|Bên\s*cấp\s*quyền|Ben\s*cap\s*quyen|Bên\s*cấp\s*phép|Ben\s*cap\s*phep|Tác\s*giả|Tac\s*gia|Copyright\s*Owner|Licensor)\s*[:.]?\s*([^\n\r,;]+)",
            r"(?:Bên\s*A|Ben\s*A)\s*(?:\([^\)]+\))?\s*[:.]?\s*([^\n\r,;]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if ":" in val:
                    val = val.split(":")[-1].strip()
                if len(val) >= 2 and not val.lower().startswith("mã số"):
                    return val
        return ""

    @staticmethod
    def _extract_distributor(text: str) -> str:
        """Trích xuất Đơn vị phân phối (distributor)"""
        patterns = [
            r"(?:Đơn\s*vị\s*phân\s*phối|Don\s*vi\s*phan\s*phoi|[·\.\s]*n\s*v[·\.\s]*\s*phân\s*ph[·\.\s]*i|Nhà\s*phân\s*phối|Nha\s*phan\s*phoi|Bên\s*phân\s*phối|Ben\s*phan\s*phoi|Bên\s*nhận\s*quyền|Ben\s*nhan\s*quyen|Bên\s*được\s*cấp\s*phép|Distributor|Licensee)\s*[:.]?\s*([^\n\r,;]+)",
            r"(?:Bên\s*B|Ben\s*B)\s*(?:\([^\)]+\))?\s*[:.]?\s*([^\n\r,;]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if ":" in val:
                    val = val.split(":")[-1].strip()
                if len(val) >= 2 and not val.lower().startswith("mã số"):
                    return val
        return ""


    @staticmethod
    def _extract_contract_id(text: str) -> str:
        """Trích xuất Mã hợp đồng (contract_id / distribution_contract_id)"""
        patterns = [
            r"(?:Mã\s*hợp\s*đồng|Ma\s*hop\s*dong|Số\s*hợp\s*đồng|So\s*hop\s*dong|Số\s*HĐ|So\s*HD|S[·\.\s]*H[·\.\s]*|HĐ\s*số|HD\s*so|Mã\s*giấy\s*phép|Số\s*giấy\s*phép|Contract\s*(?:ID|No\.?)|License\s*(?:ID|No\.?))\s*[:.]?\s*([A-Za-z0-9\/\-_]{3,35})",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                return val
        return ""

    @classmethod
    def _extract_issue_date(cls, text: str) -> str:
        """Trích xuất Ngày cấp / Ngày bắt đầu có hiệu lực (issue_date)"""
        patterns = [
            r"(?:Ngày\s*cấp|Ngay\s*cap|Ng[aà]y\s*c[·\.\s]*p|Ngày\s*bắt\s*đầu|Ngay\s*bat\s*dau|Hiệu\s*lực\s*từ\s*ngày|Hieu\s*luc\s*tu\s*ngay|Hiệu\s*lực\s*từ|Thời\s*hạn\s*từ|Thoi\s*han\s*tu|Có\s*hiệu\s*lực\s*từ|Issue\s*Date|Effective\s*Date|Start\s*Date)\s*[:.]?\s*([^\n\r]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                raw_d = m.group(1).strip()
                parsed = cls._parse_date_string(raw_d)
                if parsed:
                    return parsed
        return ""

    @classmethod
    def _extract_expiry_date(cls, text: str) -> str:
        """Trích xuất Ngày hết hạn (expiry_date) hoặc PERPETUAL"""
        # Kiểm tra vô thời hạn
        if re.search(r"\b(?:vô\s*thời\s*hạn|vo\s*thoi\s*han|vĩnh\s*viễn|vinh\s*vien|perpetual|không\s*xác\s*định\s*thời\s*hạn)\b", text, re.IGNORECASE):
            return "PERPETUAL"

        patterns = [
            r"(?:Ngày\s*hết\s*hạn|Ngay\s*het\s*han|Ng[aà]y\s*h[·\.\s]*t\s*h[·\.\s]*n|Có\s*hiệu\s*lực\s*đến|Hiệu\s*lực\s*đến|Hieu\s*luc\s*den|Thời\s*hạn\s*đến|Thoi\s*han\s*den|Đến\s*ngày|Den\s*ngay|Ngày\s*kết\s*thúc|Ngay\s*ket\s*thuc|Expiry\s*Date|Expiration\s*Date|End\s*Date)\s*[:.]?\s*([^\n\r]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                raw_d = m.group(1).strip()
                if any(w in raw_d.lower() for w in ["vô thời hạn", "vĩnh viễn", "perpetual"]):
                    return "PERPETUAL"
                parsed = cls._parse_date_string(raw_d)
                if parsed:
                    return parsed
        return ""



    @staticmethod
    def _extract_title(text: str) -> str:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            upper_line = line.upper()
            if any(k in upper_line for k in ["HÓA ĐƠN", "HOA DON", "GIẤY ĐỀ NGHỊ", "BIÊN BẢN", "THÔNG BÁO", "PHIẾU", "INVOICE", "RECEIPT", "SƠ YẾU LÝ LỊCH", "THÔNG TIN CÁ NHÂN"]):
                return line

        # Chỉ lấy dòng đầu nếu không phải là cặp key: value (như 'Họ và tên: ...')
        if lines and ":" not in lines[0] and len(lines[0]) < 60:
            return lines[0]
        return ""

    @staticmethod
    def _extract_document_no(text: str) -> str:
        patterns = [
            r"(?:HĐ\s*số|Invoice\s*No|Số\s*hóa\s*đơn|So\s*hoa\s*don|Mã\s*số\s*văn\s*bản|Số\s*văn\s*bản)\s*[:.]?\s*([A-Za-z0-9\/\-_]{3,25})",
            r"\b(?:Số|So|No\.?)\s*[:.]?\s*([A-Za-z0-9\/\-_]{3,25})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(1).strip()
                start_idx = match.start()
                preceding = text[max(0, start_idx - 15):start_idx].lower()
                val_lower = val.lower()

                # Bỏ qua nếu là số CCCD, CMND, điện thoại, tài khoản, thuế
                if any(kw in preceding for kw in ["cccd", "cmnd", "điện thoại", "dien thoai"]):
                    continue
                if any(kw in val_lower for kw in ["cccd", "cmnd", "thuế", "thue", "điện", "dien", "tiền", "tien"]):
                    continue
                if len(val) >= 3 and not (val.isalpha() and len(val) < 4):
                    return val
        return ""

    @classmethod
    def _extract_date(cls, text: str) -> str:
        # Loại trừ dòng ngày sinh để không gán nhầm ngày sinh thành ngày phát hành văn bản
        text_without_dob = re.sub(
            r"(?:Ngày\s*sinh|Ngay\s*sinh|Sinh\s*ngày|DOB|Date\s*of\s*birth)\s*[:.]?[^\n\r]+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return cls._parse_date_string(text_without_dob)

    @staticmethod
    def _parse_date_string(text: str) -> str:
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

    @staticmethod
    def _extract_dynamic_pairs(text: str, fields: Dict[str, Any], confidences: Dict[str, float], base_conf: float):
        """
        Quét các dòng dạng 'Nhãn : Giá trị' để bóc tách các trường bổ sung mà rule cứng chưa có.
        """
        alias_map = {
            # Cá nhân / Hồ sơ
            "ho_va_ten": "full_name",
            "họ_và_tên": "full_name",
            "ho_ten": "full_name",
            "họ_tên": "full_name",
            "full_name": "full_name",
            "name": "full_name",
            "ngay_sinh": "dob",
            "ngày_sinh": "dob",
            "date_of_birth": "dob",
            "dob": "dob",
            "so_cccd": "id_card_no",
            "số_cccd": "id_card_no",
            "so_cmnd": "id_card_no",
            "số_cmnd": "id_card_no",
            "cccd": "id_card_no",
            "cmnd": "id_card_no",
            "dia_chi": "address",
            "địa_chỉ": "address",
            "address": "address",
            "email": "email",
            "e_mail": "email",
            "so_dien_thoai": "phone_number",
            "số_điện_thoại": "phone_number",
            "dien_thoai": "phone_number",
            "điện_thoại": "phone_number",
            "phone": "phone_number",
            "hotline": "phone_number",
            # Hóa đơn / Chứng từ
            "ma_so_thue": "tax_code",
            "mã_số_thuế": "tax_code",
            "mst": "tax_code",
            "tax_code": "tax_code",
            "so_hoa_don": "document_no",
            "số_hóa_đơn": "document_no",
            "so": "document_no",
            "số": "document_no",
            "document_no": "document_no",
            "tong_tien": "total_amount",
            "tổng_tiền": "total_amount",
            "tong_cong": "total_amount",
            "tổng_cộng": "total_amount",
            "tong_cong_tien_thanh_toan": "total_amount",
            "tổng_cộng_tiền_thanh_toán": "total_amount",
            "thanh_tien": "total_amount",
            "thành_tiền": "total_amount",
            "total_amount": "total_amount",
            "khach_hang": "customer_name",
            "khách_hàng": "customer_name",
            "ten_khach_hang": "customer_name",
            "tên_khách_hàng": "customer_name",
            "nguoi_mua_hang": "customer_name",
            "người_mua_hàng": "customer_name",
            "customer_name": "customer_name",
            "buyer": "customer_name",
            "ngay": "date",
            "ngày": "date",
            "ngay_lap": "date",
            "ngày_lập": "date",
            "date": "date",
            # Bản quyền & Giấy phép bài hát (Song Licenses)
            "loai_ban_quyen": "license_type",
            "loại_bản_quyền": "license_type",
            "loai_giay_phep": "license_type",
            "loại_giấy_phép": "license_type",
            "loai_ban_quyen_giay_phep": "license_type",
            "loại_bản_quyền_giấy_phép": "license_type",
            "license_type": "license_type",
            "chu_so_huu": "copyright_owner",
            "chủ_sở_hữu": "copyright_owner",
            "chu_so_huu_quyen_tac_gia": "copyright_owner",
            "chủ_sở_hữu_quyền_tác_giả": "copyright_owner",
            "copyright_owner": "copyright_owner",
            "don_vi_phan_phoi": "distributor",
            "đơn_vị_phân_phối": "distributor",
            "nha_phan_phoi": "distributor",
            "nhà_phân_phối": "distributor",
            "distributor": "distributor",
            "ma_hop_dong": "contract_id",
            "mã_hợp_đồng": "contract_id",
            "so_hop_dong": "contract_id",
            "số_hợp_đồng": "contract_id",
            "so_hd": "contract_id",
            "số_hđ": "contract_id",
            "contract_id": "contract_id",
            "ngay_cap": "issue_date",
            "ngày_cấp": "issue_date",
            "ngay_bat_dau": "issue_date",
            "ngày_bắt_đầu": "issue_date",
            "issue_date": "issue_date",
            "ngay_het_han": "expiry_date",
            "ngày_hết_hạn": "expiry_date",
            "expiry_date": "expiry_date",

        }


        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines:
            if ":" in line:
                parts = line.split(":", 1)
                k_raw = parts[0].strip()
                v_raw = parts[1].strip()

                if not k_raw or not v_raw or len(k_raw) > 40:
                    continue

                k_slug = re.sub(r"[^\w\s]", "", k_raw.lower())
                k_slug = re.sub(r"\s+", "_", k_slug).strip("_")

                field_key = alias_map.get(k_slug, k_slug)

                # Nếu trường này chưa có giá trị, bổ sung ngay
                if field_key not in fields and v_raw:
                    fields[field_key] = v_raw
                    confidences[field_key] = round(base_conf * 0.95, 2)


