"""Run: python -m streamlit run app.py"""
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from joblab.analytics import load, summary, skill_counts, quality, insights

st.set_page_config(page_title="IT Jobs · Vietnam", page_icon="📊", layout="wide")
BLUE, TEAL = "#24477B", "#007F80"
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = [BLUE, TEAL, "#D58A2F", "#775A9E", "#788C9B"]
st.markdown("""<style>
.block-container {padding-top:4.5rem;max-width:1400px}
h1 {letter-spacing:-.035em} [data-testid="stMetricValue"] {color:#24477B}
[data-testid="stMetric"] {border-top:2px solid #007F80;padding-top:12px}
</style>""", unsafe_allow_html=True)

def plot(fig):
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), font=dict(family="Arial", size=13),
                      paper_bgcolor="rgba(0,0,0,0)", title_font_size=18)
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

def bar(frame, field, title):
    values = frame[field].value_counts().rename_axis(field).reset_index(name="Số tin")
    fig = px.bar(values.sort_values("Số tin"), x="Số tin", y=field, orientation="h", title=title,
                 labels={field: ""}, text="Số tin")
    fig.update_traces(textangle=0, textposition="outside", cliponaxis=False)
    fig.update_xaxes(range=[0, values["Số tin"].max() * 1.15])
    plot(fig)

@st.fragment(run_every="30s")
def dashboard():
    try:
        all_rows, tech, version, candidates, issues = load()
    except SQLAlchemyError:
        st.title("IT Jobs / Vietnam")
        st.warning("Chưa có CSDL hợp lệ. Chạy: python -m joblab.pipeline")
        return
    st.caption("DỮ LIỆU TUYỂN DỤNG · VIỆT NAM · MẪU CÔNG BỐ 2026")
    st.title("Công việc IT, nhìn từ dữ liệu")
    st.write("Khám phá tin tuyển dụng theo nghề, công nghệ và điều kiện làm việc.")
    imported = pd.Timestamp(version["imported_at"]).tz_convert("Asia/Ho_Chi_Minh").strftime("%d/%m/%Y %H:%M:%S")
    st.caption(f"Nhập dữ liệu: {imported} (UTC+7) · Phiên bản {version['id'][:10]} · Kiểm tra CSDL mỗi 30 giây khi đang mở. Đây không phải ngày cào.")
    with st.expander("Lọc dữ liệu", expanded=False):
        c1, c2, c3 = st.columns(3)
        source = c1.multiselect("Nguồn", sorted(all_rows.source.unique()), key="source")
        role = c2.multiselect("Nhóm nghề", sorted(all_rows.role.unique()), key="role")
        location = c3.multiselect("Địa điểm (nhãn kế thừa)", sorted(all_rows.location.unique()), key="location")
        c1, c2, c3 = st.columns(3)
        seniority = c1.multiselect("Cấp bậc", sorted(all_rows.seniority.unique()), key="seniority")
        model = c2.multiselect("Mô hình làm việc", sorted(all_rows.work_model.unique()), key="model")
        chosen_skills = c3.multiselect("Có ít nhất một kỹ năng", sorted(tech.skill.unique()), key="skills")
        months = st.multiselect("Tháng đăng — bỏ trống để giữ cả tin thiếu ngày", sorted(all_rows.posted_month.dropna().unique()), key="months")
    frame = all_rows.copy()
    for field, values in (("source", source), ("role", role), ("location", location), ("seniority", seniority), ("work_model", model), ("posted_month", months)):
        if values:
            frame = frame[frame[field].isin(values)]
    if chosen_skills:
        frame = frame[frame.snapshot_id.isin(tech.loc[tech.skill.isin(chosen_skills), "snapshot_id"])]
    st.caption(f"Đang xem {len(frame):,} / {len(all_rows):,} tin · Đơn vị đếm: tin đăng theo nguồn, chưa xác nhận việc làm duy nhất.")
    if frame.empty:
        st.info("Không có tin phù hợp. Hãy bỏ bớt điều kiện lọc.")
        return
    metrics = summary(frame)
    columns = st.columns(4)
    for col, label, value in zip(columns, ["Tin tuyển dụng", "Tên công ty phân biệt", "Có lương số", "Remote / toàn bộ tin"],
                                [f"{len(frame):,}", f"{metrics['companies']:,}", f"{metrics['salary_disclosure_pct']:.1f}%", f"{metrics['remote_all_pct']:.1f}%"]):
        col.metric(label, value)
    page = st.radio("Góc nhìn", ["Tổng quan", "Nghề & kỹ năng", "Lương & mô hình", "Chất lượng dữ liệu"], horizontal=True, key="page")
    if page == "Tổng quan":
        left, right = st.columns([3, 2])
        with left:
            bar(frame, "role", "Nhóm nghề trong mẫu")
        with right:
            bar(frame, "source", "Đóng góp của từng nguồn")
        left, right = st.columns(2)
        with left:
            bar(frame, "location", "Phân bố địa điểm")
        with right:
            dated = frame.dropna(subset=["posted_month"]).groupby("posted_month").size().reset_index(name="Số tin")
            plot(px.bar(dated, x="posted_month", y="Số tin", title="Tháng đăng trong tập tin quan sát", labels={"posted_month": "Tháng đăng"}))
            st.caption(f"Thiếu ngày hợp lệ: {frame.posted_date.isna().sum():,} tin. Không dùng biểu đồ này để suy ra xu hướng toàn thị trường.")
        st.subheader("Nhận xét theo bộ lọc")
        for line in insights(frame, tech):
            st.write("• " + line)
    elif page == "Nghề & kỹ năng":
        counts = skill_counts(frame, tech).head(15)
        plot(px.bar(counts.sort_values("postings"), x="postings", y="skill", orientation="h", title="15 kỹ năng xuất hiện nhiều nhất",
                    labels={"postings": "Số tin có kỹ năng", "skill": ""}, hover_data={"share_pct": ":.1f"}))
        st.caption("Mẫu số của tỷ lệ là toàn bộ tin sau lọc. Một tin có thể có nhiều kỹ năng; tổng tỷ lệ có thể vượt 100%.")
        pairs = tech.merge(frame[["snapshot_id", "role"]], on="snapshot_id").drop_duplicates(["snapshot_id", "skill"])
        if not pairs.empty:
            heat = pd.crosstab(pairs.role, pairs.skill).reindex(columns=counts.skill, fill_value=0)
            heat = heat.div(frame.groupby("role").size(), axis=0).mul(100).fillna(0)
            plot(px.imshow(heat, aspect="auto", color_continuous_scale="Blues", title="Tỷ lệ tin có kỹ năng trong từng nhóm nghề (%)", labels=dict(x="Kỹ năng", y="Nhóm nghề", color="% tin")))
        bar(frame, "seniority", "Cấp bậc — nhãn chính do dự án gốc phân loại")
    elif page == "Lương & mô hình":
        st.info("Lương là thông tin quảng cáo. Không suy ra lương thực nhận; không tự điền cận thiếu hoặc quy đổi USD. Tin không ghi kỳ lương được tách riêng.")
        basis = st.selectbox("Cơ sở gross/net", ["unknown", "gross", "net"], format_func=lambda x: {"unknown": "Không rõ gross/net", "gross": "Gross", "net": "Net"}[x])
        money = frame[frame.salary_comparable & frame.gross_net.eq(basis)].copy()
        st.caption(f"Mẫu lương so sánh: {len(money)} tin có đủ hai cận, VND, ghi rõ kỳ tháng, cơ sở {basis}. Trung điểm = (min + max) / 2.")
        if money.empty:
            st.warning("Không đủ tin cho biểu đồ lương với điều kiện này.")
        else:
            money["Trung điểm (triệu VND/tháng)"] = money.salary_midpoint / 1_000_000
            plot(px.box(money, y="role", x="Trung điểm (triệu VND/tháng)", points="all", title="Phân bố trung điểm khoảng lương", labels={"role": "Nhóm nghề"}, hover_data=["title", "source"]))
            st.dataframe(money.groupby("role").agg(n=("posting_id", "size"), median_vnd=("salary_midpoint", "median")), width="stretch")
        bar(frame, "salary_status", "Mức độ công khai và khả năng đọc lương")
        models = pd.crosstab(frame.role, frame.work_model, normalize="index").mul(100).reset_index().melt(id_vars="role", var_name="Mô hình", value_name="Tỷ lệ (%)")
        plot(px.bar(models, y="role", x="Tỷ lệ (%)", color="Mô hình", orientation="h", title="Mô hình làm việc theo nhóm nghề", labels={"role": "Nhóm nghề"}))
    else:
        plot(px.imshow(quality(frame), aspect="auto", zmin=0, zmax=100, color_continuous_scale="YlOrBr", text_auto=True,
                       title="Tỷ lệ thiếu hoặc chưa xác định theo nguồn (%)", labels=dict(x="Chỉ tiêu", y="Nguồn", color="% tin")))
        selected_candidates = candidates[candidates.left_id.isin(frame.snapshot_id) & candidates.right_id.isin(frame.snapshot_id)]
        st.subheader(f"{len(selected_candidates)} cặp nghi trùng liên nguồn trong phạm vi lọc")
        st.write("Cùng tên công ty chuẩn hóa và độ tương đồng tiêu đề ≥ 0,85 chỉ là cách tìm ứng viên. Chưa có cặp nào được tự động gộp.")
        st.dataframe(selected_candidates[["left_title", "right_title", "score", "decision"]], width="stretch", hide_index=True)
        st.download_button("Tải các cặp để kiểm tra", selected_candidates.to_csv(index=False).encode("utf-8-sig"), "duplicate_candidates.csv", "text/csv")
        with st.expander("Nhật ký kiểm tra toàn bộ phiên bản — không áp dụng bộ lọc"):
            st.dataframe(issues, width="stretch", hide_index=True)
        st.warning("Nhãn nghề/cấp bậc/địa điểm/mô hình và tech_stack kế thừa từ AI, chưa phải nhãn kiểm chứng. Bộ lọc tech gốc có thể loại BA, PM, UI/UX. Other ở địa điểm gồm cả trường hợp nhiều địa điểm hoặc thiếu thông tin.")
    with st.expander("Xem và tải dữ liệu sau lọc"):
        st.dataframe(frame[["title", "company", "source", "role", "seniority", "location", "work_model", "url"]], hide_index=True, width="stretch")
        st.download_button("Tải CSV", frame.to_csv(index=False).encode("utf-8-sig"), "filtered_postings.csv", "text/csv")
    st.caption("Nguồn: SonPhatTranDeveloper/vietnam-it-job-trends · Dữ liệu kế thừa, không cào lại · Không đại diện toàn bộ thị trường lao động.")

dashboard()
