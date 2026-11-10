"""Conservative transformations: unknown values stay unknown."""
import re
import unicodedata
from datetime import date

RULE_VERSION = "1.0.0"
ALIASES = {"js": "JavaScript", "javascript": "JavaScript", "typescript": "TypeScript",
           "ts": "TypeScript", "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
           "nodejs": "Node.js", "node.js": "Node.js", "reactjs": "React", "react.js": "React",
           "react": "React", "python": "Python", "java": "Java", "sql": "SQL",
           "c#": "C#", "c++": "C++", ".net": ".NET", "dotnet": ".NET"}
VALID = {
    "role": {"Backend", "Frontend", "Fullstack", "Mobile", "Data / AI / ML", "DevOps / SRE / Cloud",
             "QA / Testing", "Product / BA / Agile", "Security / Cyber", "Infrastructure / IT Support",
             "UI/UX Design", "Game Development", "Other", "Unknown"},
    "seniority": {"Intern", "Fresher / Entry-level", "Junior", "Mid-level", "Senior", "Lead / Principal",
                  "Manager", "Director / Executive", "Unknown"},
    "location": {"Ho Chi Minh", "Ha Noi", "Da Nang", "Other", "Unknown"},
    "work_model": {"On-site", "Hybrid", "Remote", "Unknown"},
}

def clean_text(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()

def key(value):
    return clean_text(value).casefold()

def match_key(value):
    return re.sub(r"[^\w]+", " ", key(value)).strip()

def skills(value):
    if not isinstance(value, list):
        return []
    result = {}
    for raw in value:
        text = clean_text(raw)
        if text:
            name = ALIASES.get(text.casefold(), text)
            result.setdefault(name.casefold(), name)
    return sorted(result.values(), key=str.casefold)

def parse_date(value):
    """Only explicit ISO dates. Relative times lack a trustworthy crawl timestamp."""
    if value is None or value == "":
        return None, "missing"
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].*)?", value.strip()):
        return None, "unparsed"
    try:
        return date.fromisoformat(value.strip()[:10]), "parsed"
    except ValueError:
        return None, "invalid"

def number(token):
    token = token.replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", token):
        return float(re.sub(r"[,.]", "", token))
    if token.count(",") + token.count(".") <= 1:
        return float(token.replace(",", "."))
    raise ValueError("Ambiguous numeric separators")

def salary(raw):
    out = dict(salary_status="missing", salary_min=None, salary_max=None, currency=None,
               pay_period="unknown", gross_net="unknown")
    s = key(raw)
    if not s:
        return out
    if any(x in s for x in ("sign in", "login", "đăng nhập")):
        out["salary_status"] = "hidden"
        return out
    if any(x in s for x in ("thỏa thuận", "thoả thuận", "thương lượng", "negotiable", "competitive")):
        out["salary_status"] = "negotiable"
        return out
    if any(x in s for x in ("không lương", "unpaid")):
        out.update(salary_status="unpaid", salary_min=0, salary_max=0)
        return out
    out["gross_net"] = "gross" if re.search(r"\bgross\b", s) else "net" if re.search(r"\bnet\b", s) else "unknown"
    if re.search(r"tháng|month", s):
        out["pay_period"] = "month"
    elif re.search(r"năm|year|annual", s):
        out["pay_period"] = "year"
    elif re.search(r"giờ|hour", s):
        out["pay_period"] = "hour"
    elif re.search(r"ngày|day", s):
        out["pay_period"] = "day"
    usd = bool(re.search(r"usd|\$", s))
    vnd = bool(re.search(r"vnd|vnđ|₫|đồng|triệu|\d\s*tr\b", s))
    out["currency"] = "USD" if usd and not vnd else "VND" if vnd and not usd else None
    tokens = re.findall(r"\d+(?:[.,]\d+)*", s)
    if not out["currency"] or not 1 <= len(tokens) <= 2:
        out["salary_status"] = "unparsed"
        return out
    try:
        values = [number(t) for t in tokens]
        if re.search(r"triệu|\d\s*tr\b", s):
            values = [v * 1_000_000 for v in values]
        if len(values) == 2:
            out.update(salary_status="range", salary_min=values[0], salary_max=values[1])
        elif re.search(r"tới|đến|lên đến|up to|maximum|max\b", s):
            out.update(salary_status="upper_bound", salary_max=values[0])
        elif re.search(r"từ|from|minimum|min\b|\+", s):
            out.update(salary_status="lower_bound", salary_min=values[0])
        else:
            out.update(salary_status="exact", salary_min=values[0], salary_max=values[0])
        if out["salary_min"] is not None and out["salary_max"] is not None and out["salary_min"] > out["salary_max"]:
            out.update(salary_status="invalid", salary_min=None, salary_max=None)
    except ValueError:
        out.update(salary_status="unparsed", salary_min=None, salary_max=None)
    return out
