import json
from pathlib import Path
import pytest
from sqlalchemy import text
from joblab.cleaning import salary, skills, parse_date
from joblab.pipeline import run
from joblab.analytics import load, skill_counts
from joblab.db import engine

@pytest.mark.parametrize("raw,status,low,high,period", [
    ("15 - 25 triệu", "range", 15e6, 25e6, "unknown"),
    ("Tới 30tr ₫/tháng", "upper_bound", None, 30e6, "month"),
    ("Từ 20 triệu/tháng", "lower_bound", 20e6, None, "month"),
    ("$ 1,000-1,500 /tháng", "range", 1000, 1500, "month"),
    ("200tr-500tr ₫/năm", "range", 200e6, 500e6, "year"),
    ("1,5 - 2 triệu/tháng", "range", 1.5e6, 2e6, "month"),
    ("Thoả thuận", "negotiable", None, None, "unknown"),
    ("Sign in to view salary", "hidden", None, None, "unknown"),
    (None, "missing", None, None, "unknown"),
    ("30 - 20 triệu", "invalid", None, None, "unknown"),
])
def test_salary(raw, status, low, high, period):
    result = salary(raw)
    assert (result['salary_status'], result['salary_min'], result['salary_max'], result['pay_period']) == (status, low, high, period)

def test_skills_and_dates():
    assert skills(["JS", "JavaScript", "Java", "C++", "C#"]) == ["C#", "C++", "Java", "JavaScript"]
    assert parse_date("3 days ago")[0] is None
    assert parse_date("2026-02-30")[1] == "invalid"

def row(site="a", url="https://a.example/job/1"):
    return dict(site=site, job_url=url, company="ABC", title="Python Developer", salary="20 - 30 triệu/tháng",
                date_posted="2026-10-01", extracted_info={"tech_stack": ["Python", "python", "SQL"]},
                classification={"title_category": "Backend", "seniority_category": "Junior",
                                "location_category": "Ha Noi", "work_model_category": "Remote"})

def test_transaction_idempotency_and_version_update(tmp_path):
    path = tmp_path / "jobs.jsonl"
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    path.write_text(json.dumps(row()) + '\n', encoding="utf-8")
    first = run(path, url, tmp_path / "artifacts")
    assert run(path, url, tmp_path / "artifacts")["status"] == "unchanged"
    frame, tech, version, _, _ = load(url)
    assert len(frame) == 1 and frame.skill_count.iloc[0] == 2
    assert frame.salary_midpoint.iloc[0] == 25e6
    assert skill_counts(frame, tech).postings.tolist() == [1, 1]
    # Repeated row retained in raw, but one posting; another source stays a separate posting.
    path.write_text('\n'.join(json.dumps(x) for x in [row(), row(), row("b", "https://b.example/job/2")]), encoding="utf-8")
    updated = run(path, url, tmp_path / "artifacts")
    frame, _, version, candidates, _ = load(url)
    assert len(frame) == 2 and len(candidates) == 1
    assert updated["version_id"] != first["version_id"]
    assert candidates.decision.iloc[0] == "pending"
    path.write_text('{bad json', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        run(path, url, tmp_path / "artifacts")
    assert load(url)[2]["id"] == updated["version_id"]
    path.write_text(json.dumps({"site": "a"}), encoding="utf-8")
    with pytest.raises(ValueError, match="No valid"):
        run(path, url, tmp_path / "artifacts")
    assert load(url)[2]["id"] == updated["version_id"]
    with engine(url).connect() as conn:
        assert not conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        assert conn.execute(text("SELECT COUNT(*) FROM dataset_version")).scalar() == 2
