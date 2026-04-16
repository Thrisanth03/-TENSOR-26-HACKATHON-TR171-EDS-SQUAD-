import streamlit as st
import requests
import sqlite3
import re
import smtplib
from datetime import datetime

st.set_page_config(page_title="Cyberbullying Assistant", layout="wide")

st.title("🚨 Cyberbullying Incident Response Assistant")

# ---------------- CONFIG ----------------
HF_API_KEY = "YOUR_HUGGINGFACE_API_KEY"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("reports.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    type TEXT,
    toxicity REAL,
    emotion TEXT,
    severity TEXT,
    frequency TEXT,
    summary TEXT,
    action TEXT,
    timestamp TEXT
)
""")
conn.commit()

# ---------------- FUNCTIONS ----------------

# OCR (cloud-safe placeholder)
def extract_text_from_image(image):
    return "Extracted text from image (OCR placeholder)"

# Anonymization
def anonymize(text):
    text = re.sub(r'\b[A-Z][a-z]{2,}\b', '[REDACTED]', text)
    text = re.sub(r'\d{10}', '[REDACTED]', text)
    text = re.sub(r'\S+@\S+', '[REDACTED]', text)
    return text

# HuggingFace Toxicity
def get_toxicity(text):
    API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": text})
    try:
        return response.json()[0][0]["score"]
    except:
        return 0.5

# Emotion (simple keyword logic for stability)
def get_emotion(text):
    text = text.lower()
    if "angry" in text or "hate" in text:
        return "anger"
    elif "sad" in text:
        return "sadness"
    return "neutral"

# Type classification
def classify_type(text):
    text = text.lower()
    if "kill" in text or "threat" in text:
        return "Threat"
    elif "stupid" in text or "idiot" in text:
        return "Verbal"
    elif "ignore" in text:
        return "Exclusion"
    return "General"

# Frequency logic
def get_frequency(freq, duration, text):
    if freq >= 5 or "always" in text:
        return "HIGH"
    elif freq >= 2 or "again" in text:
        return "MEDIUM"
    return "LOW"

# Severity
def calculate_severity(toxicity, b_type):
    if toxicity > 0.8 or b_type == "Threat":
        return "HIGH"
    elif toxicity > 0.4:
        return "MEDIUM"
    return "LOW"

# Action
def get_action(severity):
    if severity == "HIGH":
        return "Immediate intervention"
    elif severity == "MEDIUM":
        return "Counselor session"
    return "Monitor"

# Summary
def summarize(text):
    return text[:120]

# Email alert
def send_email(summary, severity):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("your@gmail.com", "your_app_password")

        msg = f"Subject: Cyberbullying Alert\n\nSeverity: {severity}\n\n{summary}"
        server.sendmail("your@gmail.com", "counselor@gmail.com", msg)
        server.quit()
    except:
        pass

# ---------------- INPUT ----------------

col1, col2 = st.columns(2)

with col1:
    text = st.text_area("Enter Report")
    image = st.file_uploader("Upload Image", type=["png","jpg"])

with col2:
    frequency = st.slider("Frequency", 1, 10, 1)
    duration = st.selectbox("Duration", ["days", "weeks", "months"])

# ---------------- PROCESS ----------------

if st.button("Analyze"):
    extracted = ""

    if image:
        extracted = extract_text_from_image(image)

    final_text = text + " " + extracted
    clean = anonymize(final_text)

    toxicity = get_toxicity(clean)
    emotion = get_emotion(clean)
    b_type = classify_type(clean)
    freq_level = get_frequency(frequency, duration, clean)
    severity = calculate_severity(toxicity, b_type)
    summary = summarize(clean)
    action = get_action(severity)

    if severity == "HIGH":
        send_email(summary, severity)

    # Save to DB
    cursor.execute("""
    INSERT INTO reports (text, type, toxicity, emotion, severity, frequency, summary, action, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (clean, b_type, toxicity, emotion, severity, freq_level, summary, action, str(datetime.now())))
    conn.commit()

    # ---------------- OUTPUT ----------------
    st.subheader("📊 Results")

    st.write("**Type:**", b_type)
    st.write("**Toxicity:**", round(toxicity,2))
    st.write("**Emotion:**", emotion)
    st.write("**Frequency:**", freq_level)
    st.write("**Severity:**", severity)
    st.write("**Summary:**", summary)
    st.write("**Action:**", action)

    if severity == "HIGH":
        st.error("🚨 HIGH RISK ALERT")

# ---------------- DASHBOARD ----------------

st.subheader("📊 Counselor Dashboard")

rows = cursor.execute("SELECT * FROM reports").fetchall()

for r in rows[::-1][:10]:
    st.write(f"{r[9]} | {r[2]} | {r[5]} | {r[7]}")
