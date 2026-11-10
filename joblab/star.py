"""Physical star schema, built atomically from the normalized core."""
from datetime import date
from sqlalchemy import Table, Column, Integer, String, Text, Float, Date, ForeignKey, UniqueConstraint, CheckConstraint, Index, select, insert, delete, text
from . import db

dimensions = {name: Table('dim_' + name, db.metadata,
    Column('id', Integer, primary_key=True), Column('name', String(255), nullable=False),
    Column('key', String(255), nullable=False, unique=True)) for name in db.dimensions}
dim_date = Table('dim_date', db.metadata,
    Column('date_key', Integer, primary_key=True), Column('full_date', Date, unique=True),
    Column('year', Integer), Column('quarter', Integer), Column('month', Integer),
    Column('day', Integer), Column('iso_week', Integer), Column('weekday', Integer), Column('month_label', String(7)))
dim_dataset = Table('dim_dataset', db.metadata,
    Column('id', String(64), primary_key=True), Column('input_sha256', String(64), nullable=False),
    Column('rule_version', String(30), nullable=False), Column('imported_at', String(40), nullable=False),
    Column('input_name', String(255), nullable=False), Column('row_count', Integer, nullable=False))
fact = Table('fact_job_posting', db.metadata,
    Column('snapshot_id', String(64), primary_key=True), Column('posting_id', String(64), nullable=False),
    Column('version_id', ForeignKey('dim_dataset.id'), nullable=False),
    Column('posted_date_key', ForeignKey('dim_date.date_key'), nullable=False),
    *[Column(name + '_id', ForeignKey('dim_' + name + '.id'), nullable=False)
      for name in ('source','company','role','seniority','location','work_model')],
    Column('title', Text, nullable=False), Column('title_cleaned', Text), Column('url', Text, nullable=False),
    Column('date_status', String(20), nullable=False), Column('salary_status', String(30), nullable=False),
    Column('salary_min', Float), Column('salary_max', Float), Column('currency', String(10)),
    Column('pay_period', String(20), nullable=False), Column('gross_net', String(20), nullable=False),
    Column('posting_count', Integer, nullable=False), Column('skill_count', Integer, nullable=False),
    Column('salary_numeric', Integer, nullable=False), Column('salary_midpoint', Float),
    Column('salary_range_width', Float), Column('salary_comparable', Integer, nullable=False),
    UniqueConstraint('version_id','posting_id'), CheckConstraint('posting_count = 1'),
    CheckConstraint('skill_count >= 0'), CheckConstraint('salary_numeric IN (0,1)'),
    CheckConstraint('salary_comparable IN (0,1)'))
Index('ix_fact_version_role', fact.c.version_id, fact.c.role_id)
bridge = Table('bridge_posting_skill', db.metadata,
    Column('snapshot_id', ForeignKey('fact_job_posting.snapshot_id'), primary_key=True),
    Column('skill_id', ForeignKey('dim_skill.id'), primary_key=True))

VIEW = """CREATE VIEW v_star_postings AS
SELECT f.posting_id, f.snapshot_id, f.version_id, src.name AS source, c.name AS company,
 f.title, f.title_cleaned, r.name AS role, sn.name AS seniority, l.name AS location,
 w.name AS work_model, f.url, d.full_date AS posted_date, f.date_status,
 f.salary_status, f.salary_min, f.salary_max, f.currency, f.pay_period, f.gross_net,
 f.skill_count, f.posting_count, f.salary_numeric, f.salary_midpoint, f.salary_range_width,
 f.salary_comparable, d.month_label AS posted_month
FROM fact_job_posting f
JOIN dim_source src ON src.id=f.source_id
JOIN dim_company c ON c.id=f.company_id
JOIN dim_role r ON r.id=f.role_id
JOIN dim_seniority sn ON sn.id=f.seniority_id
JOIN dim_location l ON l.id=f.location_id
JOIN dim_work_model w ON w.id=f.work_model_id
JOIN dim_date d ON d.date_key=f.posted_date_key"""

db.metadata.info["star_view"] = VIEW

def refresh(conn, version_id):
    """Caller owns the transaction; active_dataset must switch only after this succeeds."""
    for name, target in dimensions.items():
        existing = set(conn.execute(select(target.c.id)).scalars())
        rows = [dict(r) for r in conn.execute(select(db.dimensions[name])).mappings() if r['id'] not in existing]
        if rows:
            conn.execute(insert(target), rows)
    if not conn.execute(select(dim_dataset.c.id).where(dim_dataset.c.id==version_id)).scalar():
        record = conn.execute(select(db.version).where(db.version.c.id==version_id)).mappings().one()
        conn.execute(insert(dim_dataset).values(**record))
    existing_dates = set(conn.execute(select(dim_date.c.date_key)).scalars())
    if 0 not in existing_dates:
        conn.execute(insert(dim_date).values(date_key=0))
        existing_dates.add(0)
    core = conn.execute(text("""SELECT s.*, p.source_id, p.url,
        o.salary_status, o.salary_min, o.salary_max, o.currency, o.pay_period, o.gross_net,
        (SELECT COUNT(*) FROM posting_skill ps WHERE ps.snapshot_id=s.id) AS skill_count
        FROM posting_snapshot s JOIN posting p ON p.id=s.posting_id
        JOIN salary_offer o ON o.snapshot_id=s.id WHERE s.version_id=:v"""), {'v':version_id}).mappings().all()
    rows=[]
    for raw in core:
        value=raw['posted_date']
        day=date.fromisoformat(value[:10]) if isinstance(value,str) else value
        date_key=int(day.strftime('%Y%m%d')) if day else 0
        if date_key not in existing_dates:
            conn.execute(insert(dim_date).values(date_key=date_key, full_date=day, year=day.year,
                quarter=(day.month-1)//3+1, month=day.month, day=day.day, iso_week=day.isocalendar().week,
                weekday=day.isoweekday(), month_label=day.strftime('%Y-%m')))
            existing_dates.add(date_key)
        result={col:raw[col] for col in ('posting_id','version_id','source_id','company_id','role_id','seniority_id',
            'location_id','work_model_id','title','title_cleaned','url','date_status','salary_status',
            'salary_min','salary_max','currency','pay_period','gross_net','skill_count')}
        midpoint=(raw['salary_min']+raw['salary_max'])/2 if raw['salary_status'] in ('range','exact') and raw['salary_min'] is not None and raw['salary_max'] is not None else None
        result.update(snapshot_id=raw['id'], posted_date_key=date_key, posting_count=1,
            salary_numeric=int(raw['salary_status'] in ('range','exact','lower_bound','upper_bound')),
            salary_midpoint=midpoint, salary_range_width=raw['salary_max']-raw['salary_min'] if midpoint is not None else None,
            salary_comparable=int(midpoint is not None and raw['currency']=='VND' and raw['pay_period']=='month'))
        rows.append(result)
    # Rebuilding one version is safe to repeat and never deletes other versions.
    conn.execute(delete(bridge).where(bridge.c.snapshot_id.in_(select(fact.c.snapshot_id).where(fact.c.version_id==version_id))))
    conn.execute(delete(fact).where(fact.c.version_id==version_id))
    if rows:
        conn.execute(insert(fact), rows)
    links=conn.execute(select(db.posting_skill).join(db.snapshot, db.snapshot.c.id==db.posting_skill.c.snapshot_id)
                       .where(db.snapshot.c.version_id==version_id)).mappings().all()
    if links:
        conn.execute(insert(bridge), [dict(r) for r in links])
    return len(rows)

def main():
    database=db.engine()
    db.initialize(database)
    with database.begin() as conn:
        versions=list(conn.execute(select(db.version.c.id)).scalars())
        for version_id in versions:
            print(version_id[:10], refresh(conn,version_id), 'fact rows')

if __name__=='__main__':
    main()
