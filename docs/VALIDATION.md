# Kiểm tra bản kỹ thuật

## Đã chạy trên Windows, Python 3.12, SQLite

- Nhập 3.469 dòng JSONL → 3.469 posting của 5 nguồn.
- Nhập lại cùng nội dung → `unchanged`, không nhân bản.
- SQLite `integrity_check` → `ok`; `foreign_key_check` → không có vi phạm.
- 12 kiểm thử ban đầu: parser lương có/thiếu cận, đơn vị, kỳ, lương ẩn, lương thỏa thuận, cận đảo; kỹ năng; ngày không hợp lệ; nhập lặp; chuyển phiên bản; file lỗi và rollback.
- Kiểm thử dashboard bổ sung: bốn trang, lọc nguồn, trạng thái không có kết quả, không có exception.
- AppTest trên dữ liệu thật: chọn ITviec → đúng 555 tin.
- Notebook thực thi thành công cả 9 ô code; có 10 biểu đồ Plotly và nhận xét tính từ dữ liệu.
- Giao diện xem bằng Edge headless ở 1440px và 390px, đã kiểm tra ảnh chụp; chiều rộng trang không tràn ngang. Tab bàn phím chuyển focus được. Đây không phải kiểm toán accessibility đầy đủ.
- Kiểm thử tự động đầu-cuối trên DB và file mô phỏng riêng: file tăng từ 1 lên 2 tin → watcher phát hiện → transaction nhập → dashboard đang mở tự hiện 2 tin mà không click/reload. Tiến trình kiểm thử được dừng sau khi hoàn tất; không sửa dữ liệu thật.

## Kết quả kiểm tra dữ liệu, không phải chứng nhận chất lượng tuyệt đối

- 18 cặp ứng viên trùng liên nguồn; 0 cặp tự gộp. Chưa có tập nhãn để đo precision/recall.
- 1.386 tên công ty chuẩn hóa phân biệt, chưa xác minh pháp nhân.
- 56 tin có đủ hai cận lương VND và ghi rõ kỳ tháng. Không suy rộng cho các tin thiếu kỳ/lương ẩn.
- 5.433 dòng nhật ký vấn đề, có thể nhiều dòng cho một tin; không có nghĩa 5.433 tin lỗi.
- Nguồn và dữ liệu gốc được giữ nguyên byte; hash nằm trong pipeline_report.json.

## Chưa kiểm chứng

- Không chạy lại crawler và AI của dự án gốc.
- Chưa chạy MySQL thực tế; schema MySQL chỉ là bản xuất tham khảo.
- Chưa gộp tin liên nguồn hoặc xác nhận đúng toàn bộ nhãn AI.
- Chưa triển khai hosting công khai hoặc cài bộ lập lịch hệ thống. Watcher chạy khi người dùng khởi động tiến trình.
- Chưa làm báo cáo Word 40+ trang hay slide; tài liệu hiện tại là cơ sở kỹ thuật cho bước đó.


## Nâng cấp Star Schema

- 14 kiểm thử đạt, gồm bốn trang dashboard và kiểm tra phiên bản Star.
- 3.469 fact, 18.925 liên kết kỹ năng; tất cả cột chung giữa view lõi và view Star khớp.
- Kiểm thử xây lại mart không nhân bản; giữ nhiều phiên bản; lỗi mart rollback toàn bộ lần nhập mới.
- Notebook đã chạy lại từ Star. FK và integrity đều đạt.
