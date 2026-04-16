from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import re, os, sqlite3, time, requests
from datetime import datetime

app = FastAPI(title="SafeReport API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_API_KEY = os.getenv("HF_API_KEY", "")
DB_PATH = "incidents.db"


# ── Database ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            text        TEXT,
            platform    TEXT,
            frequency   TEXT,
            duration    TEXT,
            type        TEXT,
            severity    TEXT,
            toxicity    REAL,
            summary     TEXT,
            action      TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ── Input model ───────────────────────────────────────────
class Report(BaseModel):
    text: str
    platform: Optional[str] = "Unknown"
    frequency: Optional[str] = "once"   # once | few | repeated
    duration: Optional[str] = "days"    # days | weeks | months


# ── Step 1 & 2: Preprocess + Anonymize ───────────────────
def preprocess(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return text.strip()

def anonymize(text: str) -> str:
    # Remove capitalized names (simple heuristic)
    text = re.sub(r'\b[A-Z][a-z]{2,}\b', '[REDACTED]', text)
    # Remove phone numbers (10-digit, with or without spaces/dashes)
    text = re.sub(r'\b\d[\d\s\-]{8,}\d\b', '[REDACTED]', text)
    # Remove emails
    text = re.sub(r'\S+@\S+\.\S+', '[REDACTED]', text)
    return text


# ── Step 3: Bullying type classification ─────────────────
KEYWORDS = {
    "Threat": ["kill", "threaten", "hurt", "stab", "beat you up", "you will die",
                "gonna get you", "i will find you", "dead", "harm"],
    "Sexual Harassment": ["sex", "naked", "nude", "touch me", "body", "sexual",
                          "inappropriate", "send pic", "send photo"],
    "Verbal Abuse": ["stupid", "idiot", "loser", "ugly", "fat", "dumb", "worthless",
                     "hate you", "nobody likes you", "failure", "pathetic"],
    "Social Exclusion": ["ignore", "exclude", "leave out", "nobody", "no one",
                         "blocked", "kicked out", "not invited", "banned"],
}

def classify_type(text: str) -> str:
    for btype, kws in KEYWORDS.items():
        if any(kw in text for kw in kws):
            return btype
    return "General"


# ── Step 4: Frequency detection ───────────────────────────
def detect_frequency(text: str, frequency: str, duration: str) -> str:
    level = 0
    repeat_words = ["again", "always", "every day", "keeps", "constantly", "repeatedly"]
    if any(w in text for w in repeat_words):
        level += 1
    if frequency in ("few", "repeated"):
        level += 1
    if duration == "weeks":
        level += 1
    elif duration == "months":
        level += 2
    if level == 0:
        return "LOW"
    elif level <= 2:
        return "MEDIUM"
    return "HIGH"


# ── Step 5: Severity ──────────────────────────────────────
def get_toxicity(text: str) -> float:
    if not HF_API_KEY:
        return _rule_toxicity(text)
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/unitary/toxic-bert",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": text},
            timeout=8,
        )
        scores = resp.json()[0]
        toxic = next((s["score"] for s in scores if s["label"] == "toxic"), 0.5)
        return round(toxic, 4)
    except Exception:
        return _rule_toxicity(text)

def _rule_toxicity(text: str) -> float:
    t = KEYWORDS["Threat"]
    s = KEYWORDS["Sexual Harassment"]
    v = KEYWORDS["Verbal Abuse"]
    if any(w in text for w in t + s):
        return 0.9
    if any(w in text for w in v):
        return 0.6
    return 0.25

def calculate_severity(toxicity: float, btype: str, freq_level: str) -> str:
    if toxicity > 0.8 or btype == "Threat" or btype == "Sexual Harassment":
        return "HIGH"
    if toxicity > 0.4 or btype == "Verbal Abuse" or freq_level == "HIGH":
        return "MEDIUM"
    return "LOW"


# ── Step 6: Summary ───────────────────────────────────────
def generate_summary(btype: str, severity: str, platform: str,
                     frequency: str, duration: str) -> str:
    freq_desc = {"once": "a single", "few": "several", "repeated": "repeated"}
    sev_desc = {"HIGH": "serious", "MEDIUM": "concerning", "LOW": "reported"}
    return (
        f"{freq_desc.get(frequency, 'reported').capitalize()} {sev_desc.get(severity, 'reported')} "
        f"{btype.lower()} incident(s) on {platform} over {duration}."
    )


# ── Step 7: Action recommendation ────────────────────────
ACTIONS = {
    "HIGH":   "Immediate intervention required — escalate to school admin and notify parents.",
    "MEDIUM": "Schedule a counselor meeting within 48 hours.",
    "LOW":    "Monitor the situation and document for future reference.",
}


# ── Step 8: Persist ───────────────────────────────────────
def save_incident(data: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO incidents
          (timestamp, text, platform, frequency, duration, type, severity, toxicity, summary, action)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        data["timestamp"], data["text"], data["platform"],
        data["frequency"], data["duration"], data["type"],
        data["severity"], data["toxicity"], data["summary"], data["action"],
    ))
    conn.commit()
    conn.close()


# ── API ───────────────────────────────────────────────────
@app.post("/analyze")
def analyze(report: Report):
    anon   = anonymize(report.text)
    clean  = preprocess(anon)

    btype     = classify_type(clean)
    toxicity  = get_toxicity(clean)
    freq_lvl  = detect_frequency(clean, report.frequency, report.duration)
    severity  = calculate_severity(toxicity, btype, freq_lvl)
    summary   = generate_summary(btype, severity, report.platform,
                                 report.frequency, report.duration)
    action    = ACTIONS[severity]
    ts        = datetime.utcnow().isoformat()

    record = {
        "timestamp": ts, "text": anon[:300],
        "platform": report.platform, "frequency": report.frequency,
        "duration": report.duration, "type": btype,
        "severity": severity, "toxicity": toxicity,
        "summary": summary, "action": action,
    }
    save_incident(record)

    return {
        "incident_id": int(time.time() * 1000),
        "type": btype,
        "severity": severity,
        "frequency": freq_lvl,
        "toxicity": toxicity,
        "summary": summary,
        "action": action,
        "timestamp": ts,
        "platform": report.platform,
    }


@app.get("/incidents")
def get_incidents(severity: str = "", btype: str = "", limit: int = 100):
    conn = sqlite3.connect(DB_PATH)
    q = "SELECT * FROM incidents WHERE 1=1"
    params = []
    if severity:
        q += " AND severity = ?"; params.append(severity.upper())
    if btype:
        q += " AND type = ?"; params.append(btype)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    cols = [d[0] for d in conn.execute(q, params).description] if rows else []
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


@app.get("/stats")
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    high  = conn.execute("SELECT COUNT(*) FROM incidents WHERE severity='HIGH'").fetchone()[0]
    by_type = dict(conn.execute(
        "SELECT type, COUNT(*) FROM incidents GROUP BY type"
    ).fetchall())
    conn.close()
    return {"total": total, "high_severity": high, "by_type": by_type}


@app.get("/health")
def health():
    return {"status": "ok"}
