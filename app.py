import streamlit as st
import pandas as pd
import sqlite3
import re
import requests
from datetime import datetime
from PIL import Image
import numpy as np
import easyocr
import random

# ==========================================
# 🔑 CORE CONFIGURATION
# ==========================================
HF_API_KEY = "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"
C_USER, C_PASS = "admin", "SafeSchool2026"

# ==========================================
# 🏗️ BACKEND: RESOURCE CACHING
# ==========================================
@st.cache_resource
def init_db():
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidents 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, platform TEXT, 
             type TEXT, severity TEXT, emotion TEXT, summary TEXT, status TEXT, score REAL)''')

@st.cache_resource
def load_ocr_engine():
    # Cache prevents memory overflow
    return easyocr.Reader(['en'], gpu=False)

def trigger_counselor_alarm(level, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        conn.execute("INSERT INTO incidents (ts, platform, type, severity, emotion, summary, status, score) VALUES (?,?,?,?,?,?,?,?)",
                     (ts, "INTERNAL", "ALARM", level, "Panic", message, "🚨 UNREAD ALARM", 1.0))

def call_ai_models(text):
    if not text.strip():
        return 0.0, "neutral"
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    tox_api = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    emo_api = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
    
    try:
        # Increase timeout to 20s to prevent 'Neutral' defaults on slow API warmups
        t_res = requests.post(tox_api, headers=headers, json={"inputs": text}, timeout=20).json()
        e_res = requests.post(emo_api, headers=headers, json={"inputs": text}, timeout=20).json()
        
        # Extract score safely
        score = t_res[0][0]['score']
        label = e_res[0][0]['label']
        return score, label
    except Exception:
        return 0.0, "Analysis Pending"

def anonymize(text):
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    text = re.sub(r'\d{10}', '[PHONE]', text)
    return re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text)

# ==========================================
# 🎨 UI & BRANDING
# ==========================================
st.set_page_config(page_title="SafeSchool AI | Pro", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .feature-card {
        background: rgba(255, 255, 255, 0.03); padding: 30px; border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 20px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
        color: white; font-weight: 700; border-radius: 12px;
    }
    .emergency-btn button { background: #dc2626 !important; }
    .motivation-box {
        padding: 20px; background: rgba(37, 99, 235, 0.1); 
        border-left: 4px solid #3b82f6; border-radius: 10px; color: #93c5fd;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🚦 ROUTING
# ==========================================
init_db()
reader = load_ocr_engine()

if 'view' not in st.session_state: st.session_state.view = "Home"

if st.session_state.view == "Home":
    st.markdown("<h1 style='text-align:center;'>🛡️ SafeSchool AI</h1>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='feature-card'><h3>Student Portal</h3><p>Secure Anonymous Reporting</p></div>", unsafe_allow_html=True)
        if st.button("🚀 Open Terminal"): st.session_state.view = "Student"; st.rerun()
    with col_b:
        st.markdown("<div class='feature-card'><h3>Administration</h3><p>Staff Login</p></div>", unsafe_allow_html=True)
        u, p = st.text_input("Staff ID"), st.text_input("Key", type="password")
        if st.button("🔒 Login"):
            if u == C_USER and p == C_PASS: st.session_state.view = "Staff"; st.rerun()

elif st.session_state.view == "Student":
    if st.sidebar.button("🏠 Exit"): st.session_state.view = "Home"; st.rerun()
    st.markdown("<div class='motivation-box'>Every report helps build a safer school environment.</div>", unsafe_allow_html=True)

    # 1. INCIDENT ANALYSIS (TOP)
    st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
    st.markdown("### 📝 Incident Analysis Terminal")
    msg_input = st.text_area("What happened?")
    uploaded_files = st.file_uploader("Evidence (Chat Screenshots)", accept_multiple_files=True)
    
    col_1, col_2 = st.columns(2)
    platform = col_1.selectbox("Platform", ["WhatsApp", "Instagram", "Discord", "Snapchat", "Other"])
    frequency = col_2.selectbox("Frequency", ["Once", "Repeat Offense", "Constant Bullying"])
    
    if st.button("Analyze & Secure Report"):
        with st.status("🚀 AI Analysis in Progress...") as status:
            ocr_text = ""
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    img = Image.open(uploaded_file)
                    # Use numpy for OCR processing
                    res = reader.readtext(np.array(img))
                    ocr_text += " " + " ".join([r[1] for r in res])
            
            # THE FIX: Merge message box text with image text
            combined_text = msg_input + " " + ocr_text
            anonymized_text = anonymize(combined_text)
            
            # Call AI with the combined data
            toxicity_score, emotion_label = call_ai_models(anonymized_text)
            
            # Determine Severity based on score AND frequency
            if toxicity_score > 0.75 or frequency == "Constant Bullying":
                final_severity = "HIGH"
            elif toxicity_score > 0.4:
                final_severity = "MEDIUM"
            else:
                final_severity = "LOW"
            
            if final_severity == "HIGH":
                trigger_counselor_alarm("CRITICAL", "High Toxicity Incident Reported")

            # Save to Database
            with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
                conn.execute("INSERT INTO incidents (ts, platform, type, severity, emotion, summary, status, score) VALUES (?,?,?,?,?,?,?,?)",
                             (datetime.now().strftime("%Y-%m-%d %H:%M"), platform, frequency, final_severity, emotion_label, anonymized_text[:400], "Pending", toxicity_score))
            
            status.update(label="Report Secured!", state="complete")
            
            # USER RECEIPT (Confirmation for the Student)
            st.divider()
            st.subheader("📄 Report Receipt (Private)")
            st.write(f"**Severity Level:** {final_severity}")
            st.write(f"**Emotion Analysis:** {emotion_label.capitalize()}")
            st.write(f"**Processed Text:** {anonymized_text[:150]}...")
            st.success("Your report has been submitted anonymously. Thank you for speaking up.")
            st.balloons()
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. EMERGENCY BUTTONS (BOTTOM)
    st.subheader("🆘 Crisis Support")
    c_e1, c_e2 = st.columns(2)
    with c_e1:
        st.markdown('<div class="emergency-btn">', unsafe_allow_html=True)
        if st.button("🚨 IMMEDIATE HELP"):
            trigger_counselor_alarm("CRITICAL", "Manual Immediate Help Request")
            st.error("Alarm triggered. A counselor has been notified.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c_e2:
        if st.button("🤝 REQUEST PRIORITY CALL"):
            trigger_counselor_alarm("HIGH", "Call Request Logged")
            st.success("Request logged for a counselor call-back.")

elif st.session_state.view == "Staff":
    st.sidebar.button("🚪 Logout", on_click=lambda: st.session_state.update({"view": "Home"}))
    st.title("📊 Safety Command Center")
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        df = pd.read_sql_query("SELECT * FROM incidents ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True, hide_index=True)
