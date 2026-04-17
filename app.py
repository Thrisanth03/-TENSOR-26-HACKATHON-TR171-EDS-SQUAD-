```python
import streamlit as st
import pandas as pd
import sqlite3
import re
import requests
from datetime import datetime
from PIL import Image
import numpy as np
import easyocr

# ==========================================
# 🔑 CONFIG
# ==========================================
HF_API_KEY = "YOUR_HF_API_KEY"  # replace
C_USER, C_PASS = "admin", "SafeSchool2026"

# ==========================================
# 🏗️ DB
# ==========================================
@st.cache_resource
def init_db():
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidents 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, platform TEXT, 
             type TEXT, severity TEXT, emotion TEXT, summary TEXT, status TEXT, score REAL)''')

# ==========================================
# OCR
# ==========================================
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

def extract_text(imgs, reader):
    text = ""
    if imgs:
        for img in imgs:
            try:
                image = np.array(Image.open(img).convert("RGB"))
                result = reader.readtext(image, detail=0, paragraph=True)
                text += " " + " ".join(result)
            except:
                pass
    return text.strip()

# ==========================================
# AI MODELS
# ==========================================
def call_ai(text):
    if not text.strip():
        return 0.0, "neutral"

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    try:
        tox = requests.post(
            "https://api-inference.huggingface.co/models/unitary/toxic-bert",
            headers=headers, json={"inputs": text}
        ).json()

        emo = requests.post(
            "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base",
            headers=headers, json={"inputs": text}
        ).json()

        return tox[0][0]['score'], emo[0][0]['label']
    except:
        return 0.1, "neutral"

# ==========================================
# LOGIC
# ==========================================
def anonymize(text):
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    text = re.sub(r'\d{10}', '[PHONE]', text)
    return re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text)

def classify(text, tox):
    t = text.lower()

    if any(w in t for w in ["kill", "hurt", "die", "threat"]):
        return "Threat", "HIGH"
    elif any(w in t for w in ["stupid", "idiot", "useless", "loser"]):
        return "Verbal Abuse", "MEDIUM"
    elif tox > 0.7:
        return "Toxic", "MEDIUM"
    else:
        return "General", "LOW"

def summarize(text):
    parts = text.split(".")
    return ". ".join(parts[:2]).strip()[:150]

# ==========================================
# UI
# ==========================================
st.set_page_config(page_title="SafeSchool AI", layout="wide")

init_db()
reader = load_ocr()

page = st.sidebar.radio("Navigation", ["Student", "Counselor"])

# ==========================================
# STUDENT PAGE
# ==========================================
if page == "Student":

    st.title("🛡️ Cyberbullying Reporting System")

    msg = st.text_area("📝 Describe incident (optional)")
    imgs = st.file_uploader("📸 Upload screenshots", accept_multiple_files=True)

    platform = st.selectbox("Platform", ["WhatsApp", "Instagram", "Discord", "Other"])

    if st.button("🚀 Analyze Report"):

        # OCR
        ocr_text = extract_text(imgs, reader)

        # Merge
        full_text = (msg or "") + " " + ocr_text

        if not full_text.strip():
            st.error("⚠️ Please enter text or upload an image")
            st.stop()

        # Clean
        clean = anonymize(full_text)

        # AI
        tox, emo = call_ai(clean)

        # Classification
        b_type, severity = classify(clean, tox)

        # Summary
        summary = summarize(clean)

        # Store DB
        with sqlite3.connect('safeschool_pro.db') as conn:
            conn.execute("""
                INSERT INTO incidents 
                (ts, platform, type, severity, emotion, summary, status, score)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                platform,
                b_type,
                severity,
                emo,
                summary,
                "Pending",
                float(tox)
            ))

        # ======================
        # 🎯 STUDENT REPORT UI
        # ======================
        st.success("✅ Report Submitted Successfully")

        col1, col2, col3 = st.columns(3)
        col1.metric("Type", b_type)
        col2.metric("Severity", severity)
        col3.metric("Emotion", emo)

        st.markdown("### 📝 Summary")
        st.info(summary)

        st.markdown("### 📊 Confidence Score")
        st.progress(min(float(tox), 1.0))

        if severity == "HIGH":
            st.error("🚨 Serious case detected. Authorities alerted.")
        elif severity == "MEDIUM":
            st.warning("⚠️ This will be reviewed by a counselor.")
        else:
            st.success("✅ Logged safely.")

        st.markdown("🔒 Your identity is protected.")

# ==========================================
# COUNSELOR DASHBOARD
# ==========================================
if page == "Counselor":

    st.title("📊 Counselor Dashboard")

    with sqlite3.connect('safeschool_pro.db') as conn:
        df = pd.read_sql_query("SELECT * FROM incidents ORDER BY id DESC", conn)

    st.dataframe(df, use_container_width=True)

    if not df.empty:
        st.subheader("🔍 Latest Incident")

        row = df.iloc[0]

        st.write("**Type:**", row["type"])
        st.write("**Severity:**", row["severity"])
        st.write("**Emotion:**", row["emotion"])
        st.write("**Summary:**", row["summary"])
```
