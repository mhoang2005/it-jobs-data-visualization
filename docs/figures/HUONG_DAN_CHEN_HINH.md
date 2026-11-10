# Hình minh họa cho báo cáo

## Các hình

1. 01_system_overview: Sơ đồ tổng quát hệ thống phân tích và trực quan hóa tin tuyển dụng IT.
2. 02_database_3nf: Sơ đồ quan hệ của lõi CSDL 3NF, gồm 16 bảng.
3. 03_database_star: Sơ đồ Star Schema phục vụ phân tích, gồm 1 fact, 9 dimension và 1 bảng cầu.

PNG có chiều rộng 3.600 pixel. SVG là bản vector, thích hợp chèn vào Word và phóng lớn. Sơ đồ tổng quát và Star nên đặt trang ngang; sơ đồ lõi có thể đặt riêng một trang dọc. Không kéo méo tỷ lệ ảnh.

PK: khóa chính. FK: khóa ngoại. Mũi tên trên sơ đồ CSDL đi từ bảng được tham chiếu đến bảng chứa khóa ngoại. 1:N thể hiện quan hệ một–nhiều (không khẳng định mọi bản ghi phía 1 đều đã có bản ghi phía N). Một số thuộc tính mô tả được lược bớt để giữ độ dễ đọc; các khóa và quan hệ chính được thể hiện.

Grain của fact_job_posting: một tin đăng theo nguồn trong một phiên bản dữ liệu. bridge_posting_skill tách kỹ năng đa trị để tránh nhân số tin khi truy vấn KPI.

## Yêu cầu triển khai phần phương pháp trong báo cáo

Trình bày chi tiết từng bước: mục đích; dữ liệu đầu vào; quy tắc và thuật toán; công cụ/hàm sử dụng; ví dụ trước–sau; số lượng bản ghi chịu tác động; dữ liệu đầu ra; cách kiểm chứng; giới hạn. Phân biệt mô tả quy trình với kết quả kiểm thử đã thực hiện.

Các bước: kết hợp nguồn; loại trùng ban đầu; bổ sung thông tin chi tiết; lọc phạm vi công việc; tổ chức mô tả và trích xuất bằng AI; phân loại; kiểm tra và chuẩn hóa bổ sung; tìm ứng viên trùng liên nguồn; nạp lõi 3NF; tạo Star; phân tích và trực quan hóa; cập nhật phiên bản.

Mô tả rõ rằng ứng viên trùng chưa được tự động gộp; ngày không xác định và lương không rõ kỳ vẫn giữ thiếu/unknown. Hai lớp CSDL được cập nhật trong cùng giao dịch, công bố phiên bản sau khi thành công.
