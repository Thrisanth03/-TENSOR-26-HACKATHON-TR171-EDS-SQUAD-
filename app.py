
import streamlit as st
import pandas as pd
import sqlite3
import re
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime
from PIL import Image
import numpy as np
import easyocr
import random

# ==========================================
# 🔑 CONFIG
# ==========================================
HF_API_KEY = "YOUR_HF_API_KEY"
C_USER, C_PASS = "admin", "SafeSchool2026"

# ==========================================
# 🏗️ BACKEND
# ==========================================
@st.cache_resource
def init_db():
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidents 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, platform TEXT, 
             type TEXT, severity TEXT, emotion TEXT, summary TEXT, status TEXT, score REAL)''')

@st.cache_resource
def load_ocr_engine():
    return easyocr.Reader(['en'], gpu=False)

# 🔥 FIXED OCR
def extract_text_from_images(imgs, reader):
    ocr_text = ""
    if imgs:
        for img in imgs:
            try:
                image = np.array(Image.open(img).convert("RGB"))
                result = reader.readtext(image, detail=0, paragraph=True)
                ocr_text += " " + " ".join(result)
            except Exception as e:
                print("OCR Error:", e)
    return ocr_text.strip()

# ==========================================
# AI MODELS
# ==========================================
def call_ai_models(text):
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
# LOGIC FIXES
# ==========================================
def anonymize(text):
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    text = re.sub(r'\d{10}', '[PHONE]', text)
    return re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text)

# 🔥 IMPROVED CLASSIFICATION
def analyze_severity_and_type(text, tox):
    t = text.lower()

    threat_words = ["kill", "hurt", "die", "threat"]
    abuse_words = ["stupid", "idiot", "useless", "loser"]

    if any(w in t for w in threat_words):
        return "Threat", "HIGH"
    elif any(w in t for w in abuse_words):
        return "Verbal Abuse", "MEDIUM"
    elif tox > 0.7:
        return "Toxic", "MEDIUM"
    else:
        return "General", "LOW"

# 🔥 BETTER SUMMARY
def generate_summary(text):
    parts = text.split(".")
    summary = ". ".join(parts[:2]).strip()
    return summary if summary else text[:150]

# ==========================================
# UI (UNCHANGED)
# ==========================================
st.set_page_config(page_title="SafeSchool AI | Pro", layout="wide")

init_db()
reader = load_ocr_engine()

if 'view' not in st.session_state:
    st.session_state.view = "Home"

# ==========================================
# HOME
# ==========================================
if st.session_state.view == "Home":

    st.title("🛡️ SafeSchool AI")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Student Portal"):
            st.session_state.view = "Student"
            st.rerun()

    with col2:
        user = st.text_input("Staff ID")
        pwd = st.text_input("Password", type="password")

        if st.button("Login"):
            if user == C_USER and pwd == C_PASS:
                st.session_state.view = "Staff"
                st.rerun()

# ==========================================
# STUDENT
# ==========================================
elif st.session_state.view == "Student":

    if st.sidebar.button("Back"):
        st.session_state.view = "Home"
        st.rerun()

    st.subheader("Report Incident")

    msg = st.text_area("Enter details")
    imgs = st.file_uploader("Upload screenshots", accept_multiple_files=True)

    platform = st.selectbox("Platform", ["WhatsApp", "Instagram", "Other"])

    if st.button("Analyze & Submit"):

        # OCR FIX
        ocr_text = extract_text_from_images(imgs, reader)

        full_text = (msg or "") + " " + ocr_text

        if not full_text.strip():
            st.error("Enter text or upload image")
            st.stop()

        clean = anonymize(full_text)

        tox, emo = call_ai_models(clean)

        # 🔥 NEW LOGIC
        b_type, severity = analyze_severity_and_type(clean, tox)

        summary = generate_summary(clean)

        # SAVE
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

        # 🔥 STUDENT REPORT OUTPUT
        st.success("Report submitted successfully")

        col1, col2, col3 = st.columns(3)
        col1.metric("Type", b_type)
        col2.metric("Severity", severity)
        col3.metric("Emotion", emo)

        st.info(summary)

        st.progress(min(float(tox), 1.0))

        if severity == "HIGH":
            st.error("🚨 Serious issue detected")
        elif severity == "MEDIUM":
            st.warning("⚠️ Needs attention")
        else:
            st.success("Logged safely")

        st.write("🔒 Your identity is protected")

# ==========================================
# STAFF
# ==========================================
elif st.session_state.view == "Staff":

    if st.sidebar.button("Logout"):
        st.session_state.view = "Home"
        st.rerun()

    st.title("📊 Dashboard")

    with sqlite3.connect('safeschool_pro.db') as conn:
        df = pd.read_sql_query("SELECT * FROM incidents ORDER BY id DESC", conn)

    st.dataframe(df)

    if not df.empty:
        st.subheader("Latest Incident")

        row = df.iloc[0]

        st.write("Type:", row["type"])
        st.write("Severity:", row["severity"])
        st.write("Emotion:", row["emotion"])
        st.write("Summary:", row["summary"])

