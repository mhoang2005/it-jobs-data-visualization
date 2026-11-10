"""Import a published JSONL snapshot. Never crawls or calls an AI API."""
import argparse
import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
from sqlalchemy import select, insert, delete
from . import db
from .star import refresh as refresh_star, fact as star_fact
from .cleaning import RULE_VERSION, VALID, clean_text, key, match_key, skills, salary, parse_date

def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def normalized_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    # Preserve query parameters: on some sources they identify the job.
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.query, ""))

def find_candidates(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["company_key"]:
            groups[row["company_key"]].append(row)
    found = []
    for group in groups.values():
        for left, right in combinations(group, 2):
            if left["source"] == right["source"]:
                continue
            a, b = match_key(left["title"]), match_key(right["title"])
            if not a or not b:
                continue
            similarity = SequenceMatcher(None, a, b).ratio()
            if similarity >= 0.85:
                found.append(dict(left_id=left["snapshot_id"], right_id=right["snapshot_id"], score=round(similarity, 4),
                                  reason="Same normalized company; title similarity >= 0.85. Candidate only.", decision="pending"))
    return found

def run(input_path=None, database_url=None, artifact_dir=None):
    input_path = Path(input_path or db.ROOT / "data/input/published_jobs.jsonl")
    artifact_dir = Path(artifact_dir or db.ROOT / "artifacts")
    payload = input_path.read_bytes()
    input_sha = hashlib.sha256(payload).hexdigest()
    version_id = digest(input_sha + ":" + RULE_VERSION)
    # Validate the whole file before touching the database.
    records = []
    for line_no, line in enumerate(payload.decode("utf-8-sig").splitlines(), 1):
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Line {line_no}: expected JSON object")
            records.append((line_no, row))
    if not records:
        raise ValueError("Input is empty; active dataset is unchanged")
    database = db.engine(database_url)
    db.initialize(database)
    with database.connect() as conn:
        previous = conn.execute(select(db.version.c.id).where(db.version.c.id == version_id)).scalar()
        current = conn.execute(select(db.active.c.version_id).where(db.active.c.slot == 1)).scalar()
    if previous:
        with database.begin() as conn:
            present = conn.execute(select(star_fact.c.snapshot_id).where(star_fact.c.version_id == version_id).limit(1)).scalar()
            if not present:
                refresh_star(conn, version_id)
    if previous and current == version_id:
        return {"status": "unchanged", "version_id": version_id}
    if previous:
        with database.begin() as conn:
            conn.execute(delete(db.active))
            conn.execute(insert(db.active).values(slot=1, version_id=version_id))
        return {"status": "activated_existing", "version_id": version_id}

    issue_rows, snapshots, raw_rows, offers, skill_links, candidate_input = [], [], [], [], [], []
    before_after = []
    def flag(line_no, field, reason):
        issue_rows.append(dict(version_id=version_id, line_no=line_no, field=field, reason=reason))

    with database.begin() as conn:
        conn.execute(insert(db.version).values(id=version_id, input_sha256=input_sha, rule_version=RULE_VERSION,
                     imported_at=datetime.now(timezone.utc).isoformat(), input_name=input_path.name, row_count=len(records)))
        caches = {name: dict(conn.execute(select(table.c.key, table.c.id)).all()) for name, table in db.dimensions.items()}
        def dim(name, value):
            canonical = clean_text(value) or "Unknown"
            normalized = key(canonical)
            if len(normalized) > 255:
                raise ValueError(f"Dimension {name} is too long")
            if normalized not in caches[name]:
                result = conn.execute(insert(db.dimensions[name]).values(name=canonical, key=normalized))
                caches[name][normalized] = result.inserted_primary_key[0]
            return caches[name][normalized]
        existing_postings = set(conn.execute(select(db.posting.c.id)).scalars())
        seen = set()
        for line_no, row in records:
            url = normalized_url(row.get("job_url"))
            source = clean_text(row.get("site"))
            raw = dict(version_id=version_id, line_no=line_no, snapshot_id=None,
                       payload_json=json.dumps(row, ensure_ascii=False))
            if not url or not source:
                flag(line_no, "identity", "missing_or_invalid_source_url; retained in raw_record")
                raw_rows.append(raw)
                continue
            posting_id = digest(source.casefold() + "|" + url)
            snapshot_id = digest(version_id + "|" + posting_id)
            raw["snapshot_id"] = snapshot_id
            raw_rows.append(raw)
            if posting_id in seen:
                flag(line_no, "identity", "duplicate_source_url; first occurrence retained")
                continue
            seen.add(posting_id)
            if posting_id not in existing_postings:
                conn.execute(insert(db.posting).values(id=posting_id, source_id=dim("source", source), url=url))
                existing_postings.add(posting_id)
            classification = row.get("classification")
            if not isinstance(classification, dict):
                classification = {}
                flag(line_no, "classification", "missing_or_invalid_object")
            extracted = row.get("extracted_info")
            if not isinstance(extracted, dict):
                extracted = {}
            fields = {}
            for name, field in (("role", "title_category"), ("seniority", "seniority_category"),
                                ("location", "location_category"), ("work_model", "work_model_category")):
                value = clean_text(classification.get(field))
                if value not in VALID[name]:
                    flag(line_no, name, "missing_or_outside_inherited_taxonomy")
                    value = "Unknown"
                if value == "Unknown":
                    flag(line_no, name, "unknown")
                fields[f"{name}_id"] = dim(name, value)
            company = clean_text(row.get("company"))
            title = clean_text(row.get("title"))
            if not company:
                flag(line_no, "company", "missing")
            if not title:
                flag(line_no, "title", "missing")
            posted_date, date_status = parse_date(row.get("date_posted"))
            if date_status != "parsed":
                flag(line_no, "date_posted", date_status)
            parsed_salary = salary(row.get("salary"))
            if parsed_salary["salary_status"] in {"missing", "unparsed", "invalid"}:
                flag(line_no, "salary", parsed_salary["salary_status"])
            technology = extracted.get("tech_stack")
            if not isinstance(technology, list):
                flag(line_no, "tech_stack", "missing_or_invalid_list")
            normalized_skills = skills(technology)
            if not normalized_skills:
                flag(line_no, "tech_stack", "no_extracted_skills")
            snapshots.append(dict(id=snapshot_id, version_id=version_id, posting_id=posting_id,
                company_id=dim("company", company), title=title, title_cleaned=clean_text(extracted.get("title_cleaned")),
                description=row.get("description") if isinstance(row.get("description"), str) else "",
                posted_date=posted_date, date_status=date_status, **fields))
            offers.append(dict(snapshot_id=snapshot_id, **parsed_salary))
            skill_links.extend(dict(snapshot_id=snapshot_id, skill_id=dim("skill", value)) for value in normalized_skills)
            candidate_input.append(dict(snapshot_id=snapshot_id, company_key=match_key(company), title=title, source=source))
            before_after.append(dict(posting_id=posting_id, source=source, salary_raw=row.get("salary"),
                                     **parsed_salary, date_raw=row.get("date_posted"), posted_date=posted_date,
                                     tech_stack_raw=json.dumps(technology, ensure_ascii=False),
                                     tech_stack_clean=json.dumps(normalized_skills, ensure_ascii=False)))
        if not snapshots:
            raise ValueError("No valid postings; transaction rolled back")
        for table, values in ((db.snapshot, snapshots), (db.raw_record, raw_rows), (db.offer, offers), (db.posting_skill, skill_links), (db.issue, issue_rows)):
            if values:
                conn.execute(insert(table), values)
        candidates = find_candidates(candidate_input)
        if candidates:
            conn.execute(insert(db.candidate), [dict(version_id=version_id, **c) for c in candidates])
        refresh_star(conn, version_id)
        conn.execute(delete(db.active))
        conn.execute(insert(db.active).values(slot=1, version_id=version_id))

    report = dict(status="imported", version_id=version_id, input_sha256=input_sha, rules=RULE_VERSION,
                  input_rows=len(records), postings=len(snapshots), issues=len(issue_rows),
                  duplicate_candidate_pairs=len(candidates), auto_merged_pairs=0)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(before_after).to_csv(artifact_dir / "before_after.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(issue_rows).to_csv(artifact_dir / "quality_issues.csv", index=False, encoding="utf-8-sig")
    lookup = {r["snapshot_id"]: r for r in candidate_input}
    pd.DataFrame([dict(**c, left_title=lookup[c["left_id"]]["title"], right_title=lookup[c["right_id"]]["title"],
                       left_source=lookup[c["left_id"]]["source"], right_source=lookup[c["right_id"]]["source"]) for c in candidates]
                 ).to_csv(artifact_dir / "duplicate_candidates.csv", index=False, encoding="utf-8-sig")
    (artifact_dir / "pipeline_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=db.ROOT / "data/input/published_jobs.jsonl")
    parser.add_argument("--watch", action="store_true", help="Check the input file for updates; does not crawl")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    while True:
        try:
            print(json.dumps(run(args.input), ensure_ascii=False), flush=True)
        except Exception as exc:
            if not args.watch:
                raise
            print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), flush=True)
        if not args.watch:
            break
        time.sleep(max(5, args.interval))

if __name__ == "__main__":
    main()
