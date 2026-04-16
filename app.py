import streamlit as st
import pandas as pd
import sqlite3
import re
import requests
import smtplib
import json
from email.message import EmailMessage
from datetime import datetime
from PIL import Image
import numpy as np
import easyocr

# ==========================================
# 🔑 INBUILT CONFIGURATION (NO SECRETS NEEDED)
# ==========================================
# ⚠️ Replace the token below with your actual HF token
HF_API_KEY = "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" 
C_USER, C_PASS = "admin", "SafeSchool2026"

# Email Configuration (Optional)
SMTP_USER = "yourschool@gmail.com"
SMTP_PASS = "xxxx xxxx xxxx xxxx" 
COUNSELOR_EMAIL = "safety@school.com"

# --- THEME & CSS ---
st.set_page_config(page_title="SafeSchool AI | Incident Response", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .report-card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #edf2f7; }
    .header-style { color: #1e293b; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🏗️ BACKEND: DATABASE & SECURITY
# ==========================================
def init_db():
    with sqlite3.connect('safeguard_vault.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidents 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, platform TEXT, 
             type TEXT, severity TEXT, emotion TEXT, summary TEXT, 
             action TEXT, status TEXT, toxicity REAL)''')

def scrub_pii(text):
    text = re.sub(r'\S+@\S+', '[EMAIL]', text) 
    text = re.sub(r'\+?\d{10,12}', '[PHONE]', text) 
    text = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text) 
    return text

# ==========================================
# 🧠 AI ENGINE: CLOUD ANALYSIS
# ==========================================
def query_ai(text):
    # FIXED: Using HF_API_KEY variable directly, NOT st.secrets
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    tox_url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    emo_url = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
    
    try:
        tox_res = requests.post(tox_url, headers=headers, json={"inputs": text}, timeout=5).json()
        emo_res = requests.post(emo_url, headers=headers, json={"inputs": text}, timeout=5).json()
        tox_score = tox_res[0][0]['score'] if isinstance(tox_res, list) else 0.5
        top_emotion = emo_res[0][0]['label'] if isinstance(emo_res, list) else "neutral"
        return tox_score, top_emotion
    except:
        return 0.5, "uncertain"

def get_action_recommendation(severity, itype):
    if severity == "HIGH": return "🚨 Immediate Intervention required."
    if severity == "MEDIUM": return "🤝 Counselor Session: Scheduled mediation."
    return "📝 Active Monitoring."

# ==========================================
# 🖥️ FRONTEND INTERFACE
# ==========================================
init_db()

if 'session_auth' not in st.session_state:
    st.session_state.session_auth = False
    st.session_state.user_role = None

if not st.session_state.session_auth:
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.markdown("<h1 class='header-style'>SafeSchool AI Gateway</h1>", unsafe_allow_html=True)
        st.write("Ensuring a safe digital environment.")
    
    with col_r:
        portal = st.tabs(["Student (Anonymous)", "Counselor Login"])
        with portal[0]:
            if st.button("Access Anonymous Reporting", use_container_width=True):
                st.session_state.user_role = "student"; st.session_state.session_auth = True; st.rerun()
        with portal[1]:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Authorize Access", use_container_width=True):
                # FIXED: Using C_USER/C_PASS variables directly, NOT st.secrets
                if u == C_USER and p == C_PASS:
                    st.session_state.user_role = "counselor"; st.session_state.session_auth = True; st.rerun()
                else: st.error("Invalid Credentials")

else:
    if st.sidebar.button("Logout"):
        st.session_state.session_auth = False; st.rerun()

    if st.session_state.user_role == "student":
        st.markdown("<h2 class='header-style'>Incident Reporting Form</h2>", unsafe_allow_html=True)
        with st.container():
            st.markdown("<div class='report-card'>", unsafe_allow_html=True)
            u_text = st.text_area("Description")
            u_imgs = st.file_uploader("Upload Screenshots", accept_multiple_files=True)
            
            c3, c4, c5 = st.columns(3)
            plat = c3.selectbox("Platform", ["WhatsApp", "Instagram", "Discord", "Other"])
            freq = c4.selectbox("Frequency", ["Once", "Few times", "Repeatedly"])
            dur = c5.selectbox("Duration", ["Days", "Weeks", "Months"])
            
            if st.button("Process & Submit Report", type="primary", use_container_width=True):
                with st.status("AI Pipeline Running...", expanded=True) as status:
                    # OCR
                    ocr_merged = ""
                    if u_imgs:
                        reader = easyocr.Reader(['en'])
                        for img in u_imgs:
                            res = reader.readtext(np.array(Image.open(img)))
                            ocr_merged += " " + " ".join([r[1] for r in res])
                    
                    final_text = scrub_pii(u_text + " " + ocr_merged)
                    tox_score, emotion = query_ai(final_text)
                    
                    itype = "Harassment"
                    if any(w in final_text.lower() for w in ["kill", "die", "threat"]): itype = "Threat"
                    
                    sev = "LOW"
                    if tox_score > 0.7 or freq == "Repeatedly" or dur == "Months": sev = "HIGH"
                    elif tox_score > 0.4: sev = "MEDIUM"
                    
                    recom = get_action_recommendation(sev, itype)
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    with sqlite3.connect('safeguard_vault.db') as conn:
                        conn.execute('''INSERT INTO incidents 
                            (ts, platform, type, severity, emotion, summary, action, status, toxicity) 
                            VALUES (?,?,?,?,?,?,?,?,?)''', 
                            (ts, plat, itype, sev, emotion, final_text[:500], recom, "Pending", tox_score))
                    
                    status.update(label="Report Secured!", state="complete")
                    st.balloons(); st.success("Anonymously Submitted.")
            st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.user_role == "counselor":
        st.header("Counselor Command Center")
        with sqlite3.connect('safeguard_vault.db') as conn:
            df = pd.read_sql_query("SELECT * FROM incidents ORDER BY id DESC", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No reports yet.")
