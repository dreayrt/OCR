# GIAO DIỆN KIỂM THỬ OCR SERVICE (TEST HTML UI)

Thư mục này chứa giao diện web tĩnh giúp bạn kiểm thử tải file PDF thực tế và xem kết quả bóc tách dữ liệu JSON trực quan.

---

## 1. Cách Mở Giao Diện

Bạn có 2 cách cực kỳ đơn giản để mở:

### Cách 1: Mở trực tiếp bằng Trình duyệt Web (Nhanh nhất)
- Vào thư mục `test_html` trên máy tính: `E:\ocr-service\test_html\`
- Nhấp đúp chuột trực tiếp vào file **`index.html`** để mở bằng Chrome, Edge, Firefox, Brave...

### Cách 2: Khởi chạy Web Server cục bộ bằng Python
Nếu bạn muốn chạy qua HTTP Server:
```bash
# Đứng tại thư mục ocr-service
python -m http.server 3000 --directory test_html
```
Sau đó truy cập: [http://localhost:3000](http://localhost:3000)

---

## 2. Tính Năng Của Giao Diện

1. **Auto Health Check**: Tự động kiểm tra trạng thái container OCR Service (`/health`) và hiển thị đèn xanh `Server Online`.
2. **Kéo & Thả PDF (Drag & Drop)**: Hỗ trợ kéo file trực tiếp từ máy tính hoặc nhấn để chọn file.
3. **Hiển Thị Kết Quả Đa Tầng**:
   - **Thẻ dữ liệu cấu trúc (Structured Fields)**: Số hóa đơn, Ngày tháng, Mã số thuế, Tổng tiền (tự động format VND), Tên khách hàng.
   - **Chỉ số hiệu năng (Metrics Tags)**: Thời gian phản hồi (`ms`), Độ tin cậy (`Confidence %`), Công nghệ xử lý (`⚡ Direct Text` hoặc `🔍 PaddleOCR 200 DPI`).
   - **Trình xem Raw JSON**: Xem toàn bộ JSON response chuẩn hóa và nút 1-click **Sao Chép JSON** vào clipboard.
4. **Cấu hình Endpoint linh hoạt**: Cho phép đổi cổng `8001` hoặc `8000` tùy theo cổng container đang chạy.
