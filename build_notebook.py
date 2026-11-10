"""Generate an executable notebook using the exact analytics shared by the dashboard."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
md("""# Tin tuyển dụng IT Việt Nam — phân tích từ CSDL

**Mục tiêu:** mô tả cơ cấu tin tuyển dụng, công nghệ, cấp bậc, lương công khai và khác biệt giữa nguồn.

**Nguồn:** [vietnam-it-job-trends](https://github.com/SonPhatTranDeveloper/vietnam-it-job-trends), commit `ad40de27b52f2f222c703e5b55f375d53f46d814`.
Kế thừa file JSONL đã xử lý; không chạy crawler hay AI. Đơn vị phân tích là **tin đăng theo nguồn**, chưa phải số việc làm duy nhất.

Các câu hỏi:
1. Cơ cấu nguồn, nhóm nghề và địa điểm thế nào?
2. Kỹ năng nào phổ biến và khác nhau theo nhóm nghề ra sao?
3. Cơ cấu cấp bậc và mô hình làm việc thế nào?
4. Lương đủ điều kiện so sánh phân bố thế nào?
5. Chất lượng dữ liệu khác nhau thế nào giữa nguồn?

Chạy `python -m joblab.pipeline` trước. Notebook chỉ đọc CSDL; không nhập lại dữ liệu."""),
code("""from pathlib import Path
import sys
root = Path.cwd()
if not (root / 'joblab').exists():
    root = root.parent
sys.path.insert(0, str(root))
import pandas as pd
import plotly.express as px
import plotly.io as pio
from IPython.display import display, Markdown
from joblab.analytics import load, summary, skill_counts, quality, insights
px.defaults.template = 'plotly_white'
px.defaults.color_discrete_sequence = ['#24477B', '#007F80', '#D58A2F', '#775A9E']
pio.renderers.default = 'plotly_mimetype'
df, tech, version, candidates, issues = load()
display(pd.Series(version, name='Dataset provenance'))
display(pd.Series(summary(df), name='KPI'))
assert df.posting_id.is_unique
"""),
md("""## 1. Kiểm tra đầu vào và kết quả chuẩn hóa
Các ô sau đọc Star Schema qua `v_star_postings`: một dòng fact cho một tin trong một phiên bản. Lõi 3NF được giữ để quản lý dữ liệu; kỹ năng nối qua bảng cầu riêng. Bản JSON nguyên trạng được lưu riêng tại `raw_record` và file đầu vào. Nhãn AI kế thừa không được xem là nhãn kiểm chứng.
Không dùng thời gian nhập file thay cho thời gian thu thập."""),
code("""display(df.head())
display(df.dtypes.to_frame('dtype'))
display(issues)
display(pd.read_csv(root / 'artifacts/before_after.csv').head(12))"""),
md("""## 2. Cơ cấu nguồn và nhóm nghề
Số tin theo nguồn đo độ đóng góp vào mẫu, không phải thị phần của website."""),
code("""sources = df.source.value_counts().rename_axis('Nguồn').reset_index(name='Số tin')
px.bar(sources, x='Nguồn', y='Số tin', text='Số tin', title='Số tin theo nguồn').show()
roles = df.role.value_counts().rename_axis('Nhóm nghề').reset_index(name='Số tin')
px.bar(roles.sort_values('Số tin'), x='Số tin', y='Nhóm nghề', orientation='h', title='Cơ cấu nhóm nghề').show()
display(Markdown(f"Nguồn **{sources.iloc[0,0]}** chiếm **{sources.iloc[0,1]/len(df):.1%}** mẫu. Nhóm nghề đứng đầu là **{roles.iloc[0,0]}**. Kết quả phụ thuộc cơ cấu nguồn và nhãn phân loại kế thừa."))"""),
md("""## 3. Địa điểm và tháng đăng
Địa điểm là nhãn chính do dự án gốc gán. `Other` có thể gồm nhiều địa điểm, ngoài ba thành phố chính hoặc thông tin chưa đủ. Tháng đăng chỉ mô tả mẫu có ngày, không chứng minh xu hướng nhu cầu tuyển dụng."""),
code("""locations = df.location.value_counts().rename_axis('Địa điểm').reset_index(name='Số tin')
px.bar(locations, x='Địa điểm', y='Số tin', title='Phân bố địa điểm').show()
months = df.dropna(subset=['posted_month']).groupby('posted_month').size().reset_index(name='Số tin')
px.bar(months, x='posted_month', y='Số tin', labels={'posted_month':'Tháng đăng'}, title='Tháng đăng của các tin quan sát').show()
display(Markdown(f"Có **{df.posted_date.notna().sum():,}/{len(df):,}** tin có ngày hợp lệ; thiếu **{df.posted_date.isna().mean():.1%}**."))"""),
md("""## 4. Kỹ năng và quan hệ với nhóm nghề
Sử dụng `extracted_info.tech_stack`, không trộn kỹ năng nguồn với từ khóa AI. Tỷ lệ = số tin chứa kỹ năng / số tin trong nhóm. Một tin nhiều kỹ năng nên tổng tỷ lệ có thể vượt 100%."""),
code("""top = skill_counts(df, tech).head(15)
display(top)
px.bar(top.sort_values('postings'), x='postings', y='skill', orientation='h', labels={'postings':'Số tin', 'skill':'Kỹ năng'}, title='Top 15 kỹ năng').show()
pairs = tech.merge(df[['snapshot_id','role']], on='snapshot_id').drop_duplicates(['snapshot_id','skill'])
heat = pd.crosstab(pairs.role, pairs.skill).reindex(columns=top.skill, fill_value=0)
heat = heat.div(df.groupby('role').size(), axis=0).mul(100).fillna(0)
px.imshow(heat, aspect='auto', color_continuous_scale='Blues', title='Tỷ lệ tin chứa kỹ năng trong từng nhóm nghề (%)').show()
display(Markdown(f"Kỹ năng xuất hiện nhiều nhất là **{top.iloc[0]['skill']}**, có trong **{int(top.iloc[0].postings)}** tin. Đây là tần suất trong mẫu, không phải xác suất xin được việc."))"""),
md("""## 5. Cấp bậc và mô hình làm việc
Mỗi tin có một nhãn cấp bậc chính; tin tuyển nhiều cấp bậc có thể bị giản lược ở dữ liệu nguồn. Tỷ lệ Remote bên dưới dùng toàn bộ tin làm mẫu số, giữ Unknown."""),
code("""levels = df.seniority.value_counts().rename_axis('Cấp bậc').reset_index(name='Số tin')
px.bar(levels, x='Cấp bậc', y='Số tin', title='Cơ cấu cấp bậc').show()
work = pd.crosstab(df.role, df.work_model, normalize='index').mul(100).reset_index().melt(id_vars='role', var_name='Mô hình', value_name='Tỷ lệ (%)')
px.bar(work, x='role', y='Tỷ lệ (%)', color='Mô hình', labels={'role':'Nhóm nghề'}, title='Mô hình làm việc theo nhóm nghề').show()
remote = df.work_model.eq('Remote').sum()
known = df.work_model.ne('Unknown').sum()
display(Markdown(f"Remote: **{remote/len(df):.1%}** toàn mẫu; **{remote/known:.1%}** trong các tin biết mô hình. Hai tỷ lệ có mẫu số khác nhau."))"""),
md("""## 6. Lương quảng cáo: điều kiện so sánh
Không tự coi `15–25 triệu` là lương theo tháng. Không tự đổi USD, năm, giờ sang VND/tháng. Từ X hoặc tới Y chỉ có một cận, không tính trung điểm. Thỏa thuận và bị ẩn không phải 0.

Trung điểm = (cận dưới + cận trên)/2, không phải lương thực nhận. Chỉ so sánh VND, kỳ tháng ghi rõ, đủ cận; tách gross/net/unknown."""),
code("""display(pd.crosstab(df.salary_status, df.pay_period))
money = df[df.salary_comparable & df.gross_net.eq('unknown')].copy()
money['midpoint_million'] = money.salary_midpoint / 1_000_000
display(money.groupby('role').agg(n=('posting_id','size'), median_vnd=('salary_midpoint','median')))
if not money.empty:
    px.box(money, x='role', y='midpoint_million', points='all', labels={'role':'Nhóm nghề','midpoint_million':'Trung điểm (triệu VND/tháng)'}, title=f'Lương VND/tháng, không rõ gross/net — n={len(money)}').show()
display(Markdown(f"Có **{len(money)}** tin đáp ứng điều kiện của biểu đồ. Không suy rộng kết quả này cho các tin lương ẩn hoặc không ghi kỳ trả lương."))"""),
md("""## 7. Chất lượng dữ liệu và ứng viên trùng
Ứng viên được tìm bằng cùng công ty chuẩn hóa và tiêu đề tương đồng ≥ 0,85. Đây là quy tắc tìm cặp để kiểm tra, chưa được hiệu chỉnh bằng tập gán nhãn, không phải bằng chứng trùng. Không tự gộp."""),
code("""q = quality(df)
display(q)
px.imshow(q, aspect='auto', zmin=0, zmax=100, text_auto=True, color_continuous_scale='YlOrBr', title='Tỷ lệ thiếu/chưa xác định theo nguồn (%)').show()
display(candidates[['left_title','right_title','score','decision']])
display(Markdown(f"Có **{len(candidates)}** cặp nghi trùng cần kiểm tra. Số tin trong các biểu đồ vẫn là số posting theo nguồn."))"""),
md("""## 8. Kết luận mô tả và giới hạn
Các nhận xét dưới đây được tính từ CSDL, không viết sẵn số liệu. Dữ liệu gốc đã được AI viết lại mô tả và phân loại. Bộ lọc tech gốc có thể loại BA/PM/UI/UX; không đại diện tất cả nghề IT. Chưa kiểm chứng nhãn AI, chưa gộp liên nguồn, chưa đánh giá toàn bộ lỗi trích xuất."""),
code("""for line in insights(df, tech):
    display(Markdown('- ' + line))
df.to_csv(root / 'artifacts/analysis_postings.csv', index=False, encoding='utf-8-sig')
(root / 'artifacts/insights.md').write_text('# Nhận xét từ phiên bản dữ liệu ' + version['id'][:10] + '\\n\\n' + '\\n\\n'.join('- ' + line for line in insights(df, tech)), encoding='utf-8')"""),
]
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}
nbf.write(nb, ROOT / "notebooks/01_analysis.ipynb")
print("Notebook generated")
