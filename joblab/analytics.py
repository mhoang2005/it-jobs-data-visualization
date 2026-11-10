import pandas as pd
from sqlalchemy import text
from .db import engine

def load(database_url=None):
    database = engine(database_url)
    with database.connect() as conn:
        version = conn.execute(text("SELECT v.* FROM dataset_version v JOIN active_dataset a ON a.version_id=v.id WHERE a.slot=1")).mappings().one()
        params = {"version": version["id"]}
        frame = pd.read_sql(text("SELECT * FROM v_star_postings WHERE version_id=:version"), conn, params=params)
        tech = pd.read_sql(text("SELECT ps.snapshot_id, k.name AS skill FROM bridge_posting_skill ps JOIN dim_skill k ON k.id=ps.skill_id JOIN fact_job_posting s ON s.snapshot_id=ps.snapshot_id WHERE s.version_id=:version"), conn, params=params)
        candidates = pd.read_sql(text("SELECT d.*, l.title AS left_title, r.title AS right_title FROM duplicate_candidate d JOIN posting_snapshot l ON l.id=d.left_id JOIN posting_snapshot r ON r.id=d.right_id WHERE d.version_id=:version"), conn, params=params)
        issues = pd.read_sql(text("SELECT field, reason, COUNT(*) AS count FROM quality_issue WHERE version_id=:version GROUP BY field, reason"), conn, params=params)
    frame["posted_date"] = pd.to_datetime(frame["posted_date"], errors="coerce")
    frame["salary_numeric"] = frame["salary_numeric"].astype(bool)
    frame["salary_comparable"] = frame["salary_comparable"].astype(bool)
    return frame, tech, dict(version), candidates, issues

def summary(frame):
    n = len(frame)
    return {"postings": n, "companies": frame.loc[frame.company.ne("Unknown"), "company"].nunique(),
            "salary_disclosure_pct": 100 * frame.salary_numeric.mean() if n else 0,
            "remote_all_pct": 100 * frame.work_model.eq("Remote").mean() if n else 0,
            "known_work_model": int(frame.work_model.ne("Unknown").sum()),
            "salary_monthly_n": int(frame.salary_comparable.sum())}

def skill_counts(frame, tech):
    selected = tech[tech.snapshot_id.isin(frame.snapshot_id)].drop_duplicates(["snapshot_id", "skill"])
    counts = selected.groupby("skill").size().rename("postings").reset_index()
    counts["share_pct"] = counts.postings / max(len(frame), 1) * 100
    return counts.sort_values("postings", ascending=False)

def quality(frame):
    indicators = pd.DataFrame({"source": frame.source,
        "Thiếu ngày đăng hợp lệ": frame.posted_date.isna(),
        "Không có lương số": ~frame.salary_numeric,
        "Mô hình làm việc Unknown": frame.work_model.eq("Unknown"),
        "Không có kỹ năng trích xuất": frame.skill_count.eq(0)})
    return indicators.groupby("source").mean().mul(100).round(1)

def insights(frame, tech):
    if frame.empty:
        return ["Không có tin trong phạm vi lọc."]
    n = len(frame)
    sources = frame.source.value_counts()
    roles = frame.role.value_counts()
    counts = skill_counts(frame, tech)
    texts = [f"Mẫu có {n:,} tin đăng. Nguồn {sources.index[0]} chiếm {sources.iloc[0] / n:.1%}; cơ cấu tổng thể chịu ảnh hưởng của nguồn này.",
             f"Nhóm nghề {roles.index[0]} đứng đầu mẫu với {roles.iloc[0]:,} tin ({roles.iloc[0] / n:.1%}), dựa trên nhãn AI kế thừa.",
             f"Remote chiếm {frame.work_model.eq('Remote').mean():.1%} trên toàn bộ tin; {frame.work_model.eq('Unknown').mean():.1%} tin chưa rõ mô hình làm việc.",
             f"{frame.salary_numeric.mean():.1%} tin có lương số đọc được. Chỉ {int(frame.salary_comparable.sum())} tin có đủ hai cận VND và ghi rõ kỳ tháng; cần tiếp tục tách gross/net/unknown."]
    if not counts.empty:
        row = counts.iloc[0]
        texts.insert(2, f"{row['skill']} xuất hiện ở {int(row.postings)} tin ({row.share_pct:.1f}% toàn bộ mẫu). Không có kỹ năng trích xuất chưa chắc là không yêu cầu kỹ năng.")
    return texts
