# Phân tích tin tuyển dụng IT Việt Nam

Bản kỹ thuật dùng dữ liệu công bố sẵn, SQLite + SQLAlchemy, Pandas, Jupyter, Streamlit + Plotly. Không chạy crawler hoặc gọi API AI.

## Chạy nhanh trên Windows

Mở PowerShell tại thư mục này:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m joblab.pipeline
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Hoặc chạy `./start.ps1`. Nếu máy chặn script PowerShell, dùng các lệnh Python bên trên. Dashboard thường mở ở http://localhost:8501.

## Sản phẩm

- `data/input/published_jobs.jsonl`: dữ liệu công bố nguyên trạng (3.469 dòng ở bản kế thừa).
- `data/jobs.db`: CSDL SQLite, tạo bởi pipeline; có lịch sử phiên bản và view phân tích.
- `sql/schema_sqlite.sql`, `sql/schema_mysql.sql`: schema xuất từ SQLAlchemy.
- `notebooks/01_analysis.ipynb`: notebook có kết quả đã chạy, biểu đồ và nhận xét.
- `app.py`: dashboard bốn góc nhìn, bộ lọc, tải CSV, tự đọc lại DB.
- `artifacts/before_after.csv`: giá trị trước và sau chuẩn hóa.
- `artifacts/quality_issues.csv`: các vấn đề được ghi nhận; một tin có thể có nhiều vấn đề.
- `artifacts/duplicate_candidates.csv`: cặp nghi trùng để kiểm tra; chưa tự gộp.
- `artifacts/pipeline_report.json`: số lượng và hash đầu vào.
- `artifacts/insights.md`: nhận xét tính từ CSDL.
- `docs/TECHNICAL_DESIGN.md`: phương pháp, ERD, 3NF, công thức, giới hạn.
- `reference-upstream.zip`: bản nguồn tham khảo, không sửa và không chạy lại.

## Notebook

Mở `notebooks/01_analysis.ipynb` bằng VS Code/Jupyter, chọn Python của `.venv`. Notebook tìm thư mục dự án từ vị trí chạy ở root hoặc notebooks. Chạy lại từ đầu sau mỗi phiên bản dữ liệu mới để cập nhật kết quả. Có thể tạo lại notebook trống bằng `python build_notebook.py`.

## Cập nhật tự động

```powershell
.\.venv\Scripts\python.exe -m joblab.pipeline --watch --interval 60
```

Chạy watcher ở cửa sổ riêng khi cần; thay file input bằng **snapshot đầy đủ** mới. Watcher không cào web. Dashboard kiểm tra phiên bản DB mỗi 30 giây khi mở. Cùng input không tạo bản ghi lặp. Lỗi nhập không thay phiên bản DB đang dùng.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Xem `docs/VALIDATION.md` để biết các kiểm tra đã chạy và phần chưa xác nhận.

## Nguồn và ghi nhận

Kế thừa [SonPhatTranDeveloper/vietnam-it-job-trends](https://github.com/SonPhatTranDeveloper/vietnam-it-job-trends), commit `ad40de27b52f2f222c703e5b55f375d53f46d814`. Dataset đầu vào đã qua pipeline của tác giả. Không nhận các bước cào/AI là thực nghiệm đã chạy của bài này. Bản nguồn được giữ để trình bày cách thu thập.

Phần bổ sung: kiểm tra chất lượng, chuẩn hóa lương/ngày/kỹ năng bảo thủ, tìm cặp nghi trùng, CSDL theo 3NF, lớp truy vấn, chỉ số, notebook và dashboard. Đơn vị đếm là **tin đăng**, không phải việc làm duy nhất. Lương quảng cáo không phải lương thực nhận. Các nhãn AI kế thừa chưa được kiểm chứng thủ công.


## Cập nhật: lớp Star Schema

CSDL có lõi 3NF và mart Star vật lý. Notebook/dashboard đọc `v_star_postings`; pipeline cập nhật hai lớp trong cùng transaction. Xem `docs/STAR_SCHEMA.md` cho sơ đồ và định nghĩa.

Sau khi cập nhật mã nguồn, chạy `python -m joblab.star` một lần để tạo mart cho các phiên bản hiện có. Những lần nhập sau pipeline tự cập nhật mart.

## Báo cáo và trình chiếu

- [Báo cáo PDF](docs/report/Bao_cao_truc_quan_hoa_du_lieu_IT.pdf)
- [Báo cáo Word](docs/report/Bao_cao_truc_quan_hoa_du_lieu_IT.docx)
- [Slide PowerPoint](docs/report/DMH_TQHDL.pptx)
- [Ảnh minh chứng](docs/screenshots)

CSDL SQLite được tạo từ dữ liệu JSONL bằng lệnh `python -m joblab.pipeline` trong phần chạy nhanh.
