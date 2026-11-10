
CREATE TABLE company (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE dataset_version (
	id VARCHAR(64) NOT NULL,
	input_sha256 VARCHAR(64) NOT NULL,
	rule_version VARCHAR(30) NOT NULL,
	imported_at VARCHAR(40) NOT NULL,
	input_name VARCHAR(255) NOT NULL,
	row_count INTEGER NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE dim_company (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE dim_dataset (
	id VARCHAR(64) NOT NULL,
	input_sha256 VARCHAR(64) NOT NULL,
	rule_version VARCHAR(30) NOT NULL,
	imported_at VARCHAR(40) NOT NULL,
	input_name VARCHAR(255) NOT NULL,
	row_count INTEGER NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE dim_date (
	date_key INTEGER NOT NULL AUTO_INCREMENT,
	full_date DATE,
	year INTEGER,
	quarter INTEGER,
	month INTEGER,
	day INTEGER,
	iso_week INTEGER,
	weekday INTEGER,
	month_label VARCHAR(7),
	PRIMARY KEY (date_key),
	UNIQUE (full_date)
)

;


CREATE TABLE dim_location (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE dim_role (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE dim_seniority (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE dim_skill (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE dim_source (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE dim_work_model (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE location (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE `role` (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE seniority (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE skill (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE source (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE work_model (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	`key` VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (`key`)
)

;


CREATE TABLE active_dataset (
	slot INTEGER NOT NULL AUTO_INCREMENT,
	version_id VARCHAR(64) NOT NULL,
	PRIMARY KEY (slot),
	CHECK (slot = 1),
	FOREIGN KEY(version_id) REFERENCES dataset_version (id)
)

;


CREATE TABLE fact_job_posting (
	snapshot_id VARCHAR(64) NOT NULL,
	posting_id VARCHAR(64) NOT NULL,
	version_id VARCHAR(64) NOT NULL,
	posted_date_key INTEGER NOT NULL,
	source_id INTEGER NOT NULL,
	company_id INTEGER NOT NULL,
	role_id INTEGER NOT NULL,
	seniority_id INTEGER NOT NULL,
	location_id INTEGER NOT NULL,
	work_model_id INTEGER NOT NULL,
	title TEXT NOT NULL,
	title_cleaned TEXT,
	url TEXT NOT NULL,
	date_status VARCHAR(20) NOT NULL,
	salary_status VARCHAR(30) NOT NULL,
	salary_min FLOAT,
	salary_max FLOAT,
	currency VARCHAR(10),
	pay_period VARCHAR(20) NOT NULL,
	gross_net VARCHAR(20) NOT NULL,
	posting_count INTEGER NOT NULL,
	skill_count INTEGER NOT NULL,
	salary_numeric INTEGER NOT NULL,
	salary_midpoint FLOAT,
	salary_range_width FLOAT,
	salary_comparable INTEGER NOT NULL,
	PRIMARY KEY (snapshot_id),
	UNIQUE (version_id, posting_id),
	CHECK (posting_count = 1),
	CHECK (skill_count >= 0),
	CHECK (salary_numeric IN (0,1)),
	CHECK (salary_comparable IN (0,1)),
	FOREIGN KEY(version_id) REFERENCES dim_dataset (id),
	FOREIGN KEY(posted_date_key) REFERENCES dim_date (date_key),
	FOREIGN KEY(source_id) REFERENCES dim_source (id),
	FOREIGN KEY(company_id) REFERENCES dim_company (id),
	FOREIGN KEY(role_id) REFERENCES dim_role (id),
	FOREIGN KEY(seniority_id) REFERENCES dim_seniority (id),
	FOREIGN KEY(location_id) REFERENCES dim_location (id),
	FOREIGN KEY(work_model_id) REFERENCES dim_work_model (id)
)

;


CREATE TABLE posting (
	id VARCHAR(64) NOT NULL,
	source_id INTEGER NOT NULL,
	url TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(source_id) REFERENCES source (id)
)

;


CREATE TABLE quality_issue (
	id INTEGER NOT NULL AUTO_INCREMENT,
	version_id VARCHAR(64) NOT NULL,
	line_no INTEGER NOT NULL,
	field VARCHAR(50) NOT NULL,
	reason VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(version_id) REFERENCES dataset_version (id)
)

;


CREATE TABLE bridge_posting_skill (
	snapshot_id VARCHAR(64) NOT NULL,
	skill_id INTEGER NOT NULL,
	PRIMARY KEY (snapshot_id, skill_id),
	FOREIGN KEY(snapshot_id) REFERENCES fact_job_posting (snapshot_id),
	FOREIGN KEY(skill_id) REFERENCES dim_skill (id)
)

;


CREATE TABLE posting_snapshot (
	id VARCHAR(64) NOT NULL,
	version_id VARCHAR(64) NOT NULL,
	posting_id VARCHAR(64) NOT NULL,
	company_id INTEGER NOT NULL,
	role_id INTEGER NOT NULL,
	seniority_id INTEGER NOT NULL,
	location_id INTEGER NOT NULL,
	work_model_id INTEGER NOT NULL,
	title TEXT NOT NULL,
	title_cleaned TEXT,
	description TEXT,
	posted_date DATE,
	date_status VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (version_id, posting_id),
	FOREIGN KEY(version_id) REFERENCES dataset_version (id),
	FOREIGN KEY(posting_id) REFERENCES posting (id),
	FOREIGN KEY(company_id) REFERENCES company (id),
	FOREIGN KEY(role_id) REFERENCES `role` (id),
	FOREIGN KEY(seniority_id) REFERENCES seniority (id),
	FOREIGN KEY(location_id) REFERENCES location (id),
	FOREIGN KEY(work_model_id) REFERENCES work_model (id)
)

;


CREATE TABLE duplicate_candidate (
	version_id VARCHAR(64) NOT NULL,
	left_id VARCHAR(64) NOT NULL,
	right_id VARCHAR(64) NOT NULL,
	score FLOAT NOT NULL,
	reason VARCHAR(255) NOT NULL,
	decision VARCHAR(20) NOT NULL,
	PRIMARY KEY (version_id, left_id, right_id),
	FOREIGN KEY(version_id) REFERENCES dataset_version (id),
	FOREIGN KEY(left_id) REFERENCES posting_snapshot (id),
	FOREIGN KEY(right_id) REFERENCES posting_snapshot (id)
)

;


CREATE TABLE posting_skill (
	snapshot_id VARCHAR(64) NOT NULL,
	skill_id INTEGER NOT NULL,
	PRIMARY KEY (snapshot_id, skill_id),
	FOREIGN KEY(snapshot_id) REFERENCES posting_snapshot (id),
	FOREIGN KEY(skill_id) REFERENCES skill (id)
)

;


CREATE TABLE raw_record (
	version_id VARCHAR(64) NOT NULL,
	line_no INTEGER NOT NULL,
	snapshot_id VARCHAR(64),
	payload_json TEXT NOT NULL,
	PRIMARY KEY (version_id, line_no),
	FOREIGN KEY(version_id) REFERENCES dataset_version (id),
	FOREIGN KEY(snapshot_id) REFERENCES posting_snapshot (id)
)

;


CREATE TABLE salary_offer (
	snapshot_id VARCHAR(64) NOT NULL,
	salary_status VARCHAR(30) NOT NULL,
	salary_min FLOAT,
	salary_max FLOAT,
	currency VARCHAR(10),
	pay_period VARCHAR(20) NOT NULL,
	gross_net VARCHAR(20) NOT NULL,
	PRIMARY KEY (snapshot_id),
	CHECK (salary_min IS NULL OR salary_min >= 0),
	CHECK (salary_max IS NULL OR salary_max >= 0),
	CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max),
	FOREIGN KEY(snapshot_id) REFERENCES posting_snapshot (id)
)

;

CREATE INDEX ix_fact_version_role ON fact_job_posting (version_id, role_id);

CREATE VIEW v_postings AS
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
JOIN salary_offer o ON o.snapshot_id=s.id;

CREATE VIEW v_star_postings AS
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
JOIN dim_date d ON d.date_key=f.posted_date_key;
