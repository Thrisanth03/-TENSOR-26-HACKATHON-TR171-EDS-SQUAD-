import streamlit as st
import os
import re
import smtplib
from email.message import EmailMessage
import requests
# For OCR: easyocr is a lighter alternative to Google Vision for hackathons
import easyocr
import numpy as np
from PIL import Image

# --- CONFIGURATION & SECRETS ---
HF_API_KEY = st.secrets["HF_API_KEY"]  # Set in HF Space Settings
EMAIL_PASS = st.secrets["EMAIL_PASS"]  # Gmail App Password
COUNSELOR_EMAIL = "counselor@school.com"

# --- CORE FUNCTIONS ---

def get_ocr_text(image):
    reader = easyocr.Reader(['en'])
    result = reader.readtext(np.array(image))
    return " ".join([res[1] for res in result])

def anonymize(text):
    # Redact Emails, Phones, and Capitalized Names
    text = re.sub(r'\S+@\S+', '[REDACTED]', text)
    text = re.sub(r'\d{10}', '[REDACTED]', text)
    return text

def cloud_ai_analysis(text):
    # Calling Hugging Face Inference API (BERT-based toxicity model)
    API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": text})
    # Simplified for the guide: returns a toxicity score
    data = response.json()
    return data[0][0]['score'] if isinstance(data, list) else 0.5

def send_alert(summary, severity):
    msg = EmailMessage()
    msg.set_content(f"URGENT: High Severity Incident\n\nSummary: {summary}\nAction: Immediate Intervention")
    msg['Subject'] = f"🚨 ALERT: {severity} Severity Cyberbullying"
    msg['From'] = "system@school.com"
    msg['To'] = COUNSELOR_EMAIL
    # Setup SMTP here (Gmail)
    # with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp: ...

# --- STREAMLIT UI ---
st.title("🛡️ Cyberbullying Incident Assistant")

tab1, tab2 = st.tabs(["Student Report", "Counselor Dashboard"])

with tab1:
    user_text = st.text_area("Describe the incident")
    u_file = st.file_uploader("Upload evidence screenshot", type=['png', 'jpg'])
    
    if st.button("Submit Report"):
        with st.spinner("Analyzing..."):
            # 1. OCR & Merge
            ocr_text = get_ocr_text(Image.open(u_file)) if u_file else ""
            final_text = anonymize(user_text + " " + ocr_text)
            
            # 2. AI Analysis
            tox_score = cloud_ai_analysis(final_text)
            
            # 3. Severity Logic
            severity = "HIGH" if tox_score > 0.8 else "MEDIUM" if tox_score > 0.4 else "LOW"
            
            # 4. Action & Alert
            if severity == "HIGH":
                send_alert(final_text[:100], severity)
                st.error("Priority 1: Counselor has been alerted.")
            
            st.success("Report Submitted Anonymously.")
            st.json({"toxicity": tox_score, "severity": severity, "action": "Follow Protocol"})

with tab2:
    st.header("Counselor View")
    st.info("Log of incidents would appear here from SQLite/Firebase.")
