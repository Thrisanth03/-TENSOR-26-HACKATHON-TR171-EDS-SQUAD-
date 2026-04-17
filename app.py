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
# 🏗️ BACKEND: RESOURCE CACHING (PREVENTS CRASHES)
# ==========================================
@st.cache_resource
def init_db():
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidents 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, platform TEXT, 
             type TEXT, severity TEXT, emotion TEXT, summary TEXT, status TEXT, score REAL)''')

@st.cache_resource
def load_ocr_engine():
    # Load once and cache to save 500MB+ RAM
    return easyocr.Reader(['en'], gpu=False)

def play_alarm():
    audio_html = """<audio autoplay><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mpeg"></audio>"""
    st.markdown(audio_html, unsafe_allow_html=True)

def trigger_counselor_alarm(level="CRITICAL", message="Alert"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        conn.execute("INSERT INTO incidents (ts, platform, type, severity, emotion, summary, status, score) VALUES (?,?,?,?,?,?,?,?)",
                     (ts, "INTERNAL", "IMMEDIATE HELP", level, "Panic", message, "🚨 UNREAD ALARM", 1.0))

def call_ai_models(text):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    tox_api = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    emo_api = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
    try:
        t_res = requests.post(tox_api, headers=headers, json={"inputs": text}, timeout=10).json()
        e_res = requests.post(emo_api, headers=headers, json={"inputs": text}, timeout=10).json()
        return t_res[0][0]['score'], e_res[0][0]['label']
    except: return 0.5, "Neutral"

def anonymize(text):
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    text = re.sub(r'\d{10}', '[PHONE]', text)
    return re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text)

# ==========================================
# 🎨 UI & STYLING
# ==========================================
st.set_page_config(page_title="SafeSchool AI | Pro", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .feature-card {
        background: rgba(255, 255, 255, 0.03); padding: 30px; border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 25px;
    }
    .stButton>button {
        width: 100%; border-radius: 12px; height: 3.5em; 
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
        color: white; font-weight: 700; border: none;
    }
    .emergency-btn button { background: #dc2626 !important; }
    .motivation-box {
        padding: 20px; background: rgba(37, 99, 235, 0.1); 
        border-left: 4px solid #3b82f6; border-radius: 12px;
        color: #93c5fd; margin-bottom: 30px; font-style: italic;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🚦 MAIN APP LOGIC
# ==========================================
init_db()
reader = load_ocr_engine()

if 'view' not in st.session_state: st.session_state.view = "Home"

if st.session_state.view == "Home":
    st.markdown("<h1 style='text-align:center;'>🛡️ SafeSchool AI</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='feature-card'><h3>Student Portal</h3><p>Secure Anonymous Reporting</p></div>", unsafe_allow_html=True)
        if st.button("🚀 Access Terminal"): st.session_state.view = "Student"; st.rerun()
    with c2:
        st.markdown("<div class='feature-card'><h3>Administration</h3><p>Staff Login</p></div>", unsafe_allow_html=True)
        u = st.text_input("Staff ID")
        p = st.text_input("Key", type="password")
        if st.button("🔒 Login"):
            if u == C_USER and p == C_PASS: st.session_state.view = "Staff"; st.rerun()

elif st.session_state.view == "Student":
    if st.sidebar.button("🏠 Exit"): st.session_state.view = "Home"; st.rerun()
    
    st.markdown("<div class='motivation-box'>Your safety is our priority. Every report is anonymous.</div>", unsafe_allow_html=True)

    # 1. Terminal First
    st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
    st.markdown("### 📝 Incident Analysis Terminal")
    msg = st.text_area("What happened?")
    imgs = st.file_uploader("Screenshots", accept_multiple_files=True)
    
    if st.button("Analyze & Secure Report"):
        with st.status("AI Processing...") as s:
            ocr_text = ""
            if imgs:
                for img in imgs:
                    res = reader.readtext(np.array(Image.open(img)))
                    ocr_text += " " + " ".join([r[1] for r in res])
            
            clean = anonymize(msg + " " + ocr_text)
            tox, emo = call_ai_models(clean)
            
            if tox >= 0.8: trigger_counselor_alarm("HIGH TOXICITY", "AI Detected Critical Content")
            
            with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
                conn.execute("INSERT INTO incidents (ts, platform, type, severity, emotion, summary, status, score) VALUES (?,?,?,?,?,?,?,?)",
                             (datetime.now().strftime("%H:%M"), "Report", "Cyberbullying", "HIGH" if tox > 0.7 else "LOW", emo, clean[:300], "Pending", tox))
            st.success("Report Submitted Safely."); st.balloons()
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. Emergency Section Second
    st.subheader("🆘 Crisis Support")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="emergency-btn">', unsafe_allow_html=True)
        if st.button("🚨 IMMEDIATE HELP"):
            play_alarm()
            trigger_counselor_alarm("CRITICAL", "Manual Immediate Help Triggered")
            st.error("Alarm sent to counselor.")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        if st.button("🤝 REQUEST CALL"):
            trigger_counselor_alarm("HIGH", "Call Request")
            st.success("Request logged.")

elif st.session_state.view == "Staff":
    st.sidebar.button("🚪 Logout", on_click=lambda: st.session_state.update({"view": "Home"}))
    with sqlite3.connect('safeschool_pro.db', check_same_thread=False) as conn:
        df = pd.read_sql_query("SELECT * FROM incidents ORDER BY id DESC", conn)
    
    if not df.empty:
        if not df[df.status == "🚨 UNREAD ALARM"].empty: play_alarm()
        st.dataframe(df, use_container_width=True)
    else: st.info("No reports.")
