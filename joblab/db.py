import os
from pathlib import Path
from sqlalchemy import (MetaData, Table, Column, Integer, String, Text, Float, Date, ForeignKey,
                        UniqueConstraint, CheckConstraint, create_engine, event, inspect)

ROOT = Path(__file__).resolve().parents[1]
metadata = MetaData()
version = Table("dataset_version", metadata,
    Column("id", String(64), primary_key=True), Column("input_sha256", String(64), nullable=False),
    Column("rule_version", String(30), nullable=False), Column("imported_at", String(40), nullable=False),
    Column("input_name", String(255), nullable=False), Column("row_count", Integer, nullable=False))
active = Table("active_dataset", metadata, Column("slot", Integer, primary_key=True),
    Column("version_id", ForeignKey("dataset_version.id"), nullable=False), CheckConstraint("slot = 1"))

def dimension(name):
    return Table(name, metadata, Column("id", Integer, primary_key=True, autoincrement=True),
                 Column("name", String(255), nullable=False), Column("key", String(255), unique=True, nullable=False))

dimensions = {name: dimension(name) for name in ("source", "company", "role", "seniority", "location", "work_model", "skill")}
posting = Table("posting", metadata, Column("id", String(64), primary_key=True),
    Column("source_id", ForeignKey("source.id"), nullable=False), Column("url", Text, nullable=False))
snapshot = Table("posting_snapshot", metadata,
    Column("id", String(64), primary_key=True), Column("version_id", ForeignKey("dataset_version.id"), nullable=False),
    Column("posting_id", ForeignKey("posting.id"), nullable=False),
    *[Column(f"{name}_id", ForeignKey(f"{name}.id"), nullable=False) for name in ("company", "role", "seniority", "location", "work_model")],
    Column("title", Text, nullable=False), Column("title_cleaned", Text), Column("description", Text),
    Column("posted_date", Date), Column("date_status", String(20), nullable=False),
    UniqueConstraint("version_id", "posting_id"))
raw_record = Table("raw_record", metadata,
    Column("version_id", ForeignKey("dataset_version.id"), primary_key=True), Column("line_no", Integer, primary_key=True),
    Column("snapshot_id", ForeignKey("posting_snapshot.id")), Column("payload_json", Text, nullable=False))
offer = Table("salary_offer", metadata, Column("snapshot_id", ForeignKey("posting_snapshot.id"), primary_key=True),
    Column("salary_status", String(30), nullable=False), Column("salary_min", Float), Column("salary_max", Float),
    Column("currency", String(10)), Column("pay_period", String(20), nullable=False), Column("gross_net", String(20), nullable=False),
    CheckConstraint("salary_min IS NULL OR salary_min >= 0"), CheckConstraint("salary_max IS NULL OR salary_max >= 0"),
    CheckConstraint("salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max"))
posting_skill = Table("posting_skill", metadata,
    Column("snapshot_id", ForeignKey("posting_snapshot.id"), primary_key=True),
    Column("skill_id", ForeignKey("skill.id"), primary_key=True))
issue = Table("quality_issue", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True), Column("version_id", ForeignKey("dataset_version.id"), nullable=False),
    Column("line_no", Integer, nullable=False), Column("field", String(50), nullable=False), Column("reason", String(255), nullable=False))
candidate = Table("duplicate_candidate", metadata,
    Column("version_id", ForeignKey("dataset_version.id"), primary_key=True),
    Column("left_id", ForeignKey("posting_snapshot.id"), primary_key=True),
    Column("right_id", ForeignKey("posting_snapshot.id"), primary_key=True),
    Column("score", Float, nullable=False), Column("reason", String(255), nullable=False),
    Column("decision", String(20), nullable=False, default="pending"))

VIEW = """CREATE VIEW v_postings AS
SELECT p.id AS posting_id, s.id AS snapshot_id, s.version_id, src.name AS source,
 c.name AS company, s.title, s.title_cleaned, r.name AS role, sn.name AS seniority,
 l.name AS location, w.name AS work_model, p.url, s.posted_date, s.date_status,
 o.salary_status, o.salary_min, o.salary_max, o.currency, o.pay_period, o.gross_net,
 (SELECT COUNT(*) FROM posting_skill ps WHERE ps.snapshot_id=s.id) AS skill_count
FROM posting_snapshot s
JOIN posting p ON p.id=s.posting_id
JOIN source src ON src.id=p.source_id
JOIN company c ON c.id=s.company_id
JOIN role r ON r.id=s.role_id
JOIN seniority sn ON sn.id=s.seniority_id
JOIN location l ON l.id=s.location_id
JOIN work_model w ON w.id=s.work_model_id
JOIN salary_offer o ON o.snapshot_id=s.id"""

def engine(url=None):
    (ROOT / "data").mkdir(exist_ok=True)
    url = url or os.environ.get("DATABASE_URL") or f"sqlite:///{(ROOT / 'data/jobs.db').as_posix()}"
    result = create_engine(url)
    if result.dialect.name == "sqlite":
        @event.listens_for(result, "connect")
        def sqlite_settings(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("PRAGMA journal_mode=WAL")
    return result

def initialize(db):
    if "fact_job_posting" not in metadata.tables:
        from . import star
    metadata.create_all(db)
    if "v_postings" not in inspect(db).get_view_names():
        with db.begin() as conn:
            conn.exec_driver_sql(VIEW)
    if "v_star_postings" not in inspect(db).get_view_names():
        with db.begin() as conn:
            conn.exec_driver_sql(metadata.info["star_view"])
