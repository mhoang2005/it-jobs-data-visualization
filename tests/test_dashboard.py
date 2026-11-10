import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from joblab.pipeline import run

def test_pages_filters_and_empty_state(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'app.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    data = tmp_path / "input.jsonl"
    common = dict(company="Fixture", title="Synthetic role", salary="20 - 30 triệu/tháng",
                  extracted_info={"tech_stack": ["Python"]})
    rows = [dict(common, site="a", job_url="https://example.invalid/a", classification={"title_category":"Backend", "work_model_category":"Remote"}),
            dict(common, site="b", job_url="https://example.invalid/b", classification={"title_category":"Frontend", "work_model_category":"On-site"})]
    data.write_text('\n'.join(json.dumps(r) for r in rows), encoding="utf-8")
    run(data, url, tmp_path / "artifacts")
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert app.metric[0].value == "2"
    for page in ["Nghề & kỹ năng", "Lương & mô hình", "Chất lượng dữ liệu", "Tổng quan"]:
        app.radio(key="page").set_value(page).run()
        assert not app.exception
    app.multiselect(key="source").set_value(["a"]).run()
    assert app.metric[0].value == "1"
    app.multiselect(key="role").set_value(["Frontend"]).run()
    assert not app.exception
    assert any("Không có tin phù hợp" in item.value for item in app.info)
