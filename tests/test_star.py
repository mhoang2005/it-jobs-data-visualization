import json
import pytest
import pandas as pd
from sqlalchemy import text
from joblab import db, star
from joblab.pipeline import run
from joblab.analytics import load

def test_star_version_grain_and_atomicity(tmp_path, monkeypatch):
    url=f"sqlite:///{(tmp_path/'star.db').as_posix()}"
    path=tmp_path/'input.jsonl'
    item=dict(site='a', job_url='https://example.invalid/1', company='C', title='Developer',
              salary='20 - 30 triệu/tháng', extracted_info={'tech_stack':['Python','SQL']},
              classification={'title_category':'Backend','seniority_category':'Junior','location_category':'Ha Noi','work_model_category':'Remote'})
    path.write_text(json.dumps(item),encoding='utf-8')
    first=run(path,url,tmp_path/'artifacts')['version_id']
    with db.engine(url).begin() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM fact_job_posting')).scalar()==1
        assert conn.execute(text('SELECT COUNT(*) FROM bridge_posting_skill')).scalar()==2
        assert conn.execute(text('SELECT posted_date_key FROM fact_job_posting')).scalar()==0
        assert conn.execute(text('SELECT full_date FROM dim_date WHERE date_key=0')).scalar() is None
        star.refresh(conn, first)
        star.refresh(conn, first)
        assert conn.execute(text('SELECT SUM(posting_count) FROM fact_job_posting')).scalar()==1
    second=dict(item, job_url='https://example.invalid/2',date_posted='2026-10-01')
    path.write_text('\n'.join(json.dumps(x) for x in [item,second]),encoding='utf-8')
    second_version=run(path,url,tmp_path/'artifacts')['version_id']
    frame, tech, _, _, _=load(url)
    assert len(frame)==2 and len(tech)==4
    assert frame.salary_midpoint.tolist()==[25e6,25e6]
    with db.engine(url).connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM fact_job_posting')).scalar()==3
        assert not conn.exec_driver_sql('PRAGMA foreign_key_check').all()
    # All core writes and mart writes roll back together if mart refresh fails.
    from joblab import pipeline
    def fail(conn,version):
        raise RuntimeError('simulated mart failure')
    monkeypatch.setattr(pipeline,'refresh_star',fail)
    path.write_text(json.dumps(dict(item,title='Changed')),encoding='utf-8')
    with pytest.raises(RuntimeError,match='simulated'):
        run(path,url,tmp_path/'artifacts')
    assert load(url)[2]['id']==second_version
    with db.engine(url).connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM dataset_version')).scalar()==2
