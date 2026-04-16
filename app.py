import streamlit as st
from transformers import pipeline
import re
import sqlite3
from datetime import datetime
from PIL import Image
import pytesseract

st.set_page_config(page_title="Cyberbullying Analyzer", layout="centered")

st.title("🚨 Cyberbullying Incident Response Assistant")

# ---------------- LOAD MODELS ----------------
@st.cache_resource
def load_models():
    classifier = pipeline("text-classification", model="unitary/toxic-bert")
    emotion_model = pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base"
    )
    return classifier, emotion_model

classifier, emotion_model = load_models()

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
    summary TEXT,
    action TEXT,
    timestamp TEXT
)
""")
conn.commit()

# ---------------- FUNCTIONS ----------------
def extract_text_from_image(image):
    return pytesseract.image_to_string(image)

def anonymize(text):
    text = re.sub(r'\b[A-Z][a-z]{2,}\b', '[REDACTED]', text)
    text = re.sub(r'\b\d{10}\b', '[REDACTED]', text)
    text = re.sub(r'\S+@\S+', '[REDACTED]', text)
    return text

def classify_type(text):
    text = text.lower()
    if any(w in text for w in ["kill","hurt","threat"]):
        return "Threat"
    elif any(w in text for w in ["stupid","idiot","loser"]):
        return "Verbal"
    elif any(w in text for w in ["ignore","exclude"]):
        return "Exclusion"
    return "General"

def calculate_severity(toxicity):
    if toxicity > 0.8:
        return "HIGH"
    elif toxicity > 0.4:
        return "MEDIUM"
    return "LOW"

def get_action(severity):
    if severity == "HIGH":
        return "Immediate intervention"
    elif severity == "MEDIUM":
        return "Counselor session"
    return "Monitor"

def simple_summary(text):
    return text[:120]

# ---------------- INPUT ----------------
text = st.text_area("Enter Report")
image_file = st.file_uploader("Upload Image", type=["png","jpg","jpeg"])

# ---------------- ANALYZE ----------------
if st.button("Analyze"):
    if text.strip() == "" and image_file is None:
        st.warning("Please enter text or upload an image")
    else:
        try:
            extracted_text = ""

            if image_file:
                image = Image.open(image_file)
                extracted_text = extract_text_from_image(image)

            final_text = text + " " + extracted_text
            clean = anonymize(final_text)

            # AI Models
            result = classifier(clean)[0]
            toxicity = result['score']
            emotion = emotion_model(clean)[0]['label']

            # Logic
            b_type = classify_type(clean)
            severity = calculate_severity(toxicity)
            summary = simple_summary(clean)
            action = get_action(severity)

            # Store in DB
            cursor.execute("""
            INSERT INTO reports (text, type, toxicity, emotion, severity, summary, action, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (clean, b_type, toxicity, emotion, severity, summary, action, str(datetime.now())))
            conn.commit()

            # ---------------- OUTPUT ----------------
            st.subheader("Results")

            if severity == "HIGH":
                st.error("HIGH RISK 🚨")
            elif severity == "MEDIUM":
                st.warning("MEDIUM RISK ⚠️")
            else:
                st.success("LOW RISK ✅")

            st.write("**Type:**", b_type)
            st.write("**Toxicity Score:**", round(toxicity, 2))
            st.write("**Emotion:**", emotion)
            st.write("**Summary:**", summary)
            st.write("**Action:**", action)

        except Exception as e:
            st.error("Error occurred")
            st.text(str(e))

# ---------------- DASHBOARD ----------------
st.subheader("📊 Incident Dashboard")

rows = cursor.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

for row in rows[:10]:
    st.write(f"🔹 {row[8]} | {row[2]} | {row[5]}")
