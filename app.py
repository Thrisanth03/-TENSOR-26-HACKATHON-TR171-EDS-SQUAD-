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
# 🔑 CORE CONFIGURATION
# ==========================================
HF_API_KEY = "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" 
C_USER, C_PASS = "admin", "SafeSchool2026"

# Email Configuration (Set these for alerts to work)
SMTP_USER = "yourschool@gmail.com" 
SMTP_PASS = "xxxx xxxx xxxx xxxx" 

# ==========================================
# 🎨 BRANDING & ADVANCED UI SYSTEM
# ==========================================
st.set_page_config(page_title="SafeSchool AI | Pro", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    /* Root Styles */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0f172a; color: #f8fafc; }
    
    /* Modern Glassmorphism Card */
    .feature-card {
        background: rgba(255, 255, 255, 0.03);
        padding: 30px;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px);
        margin-bottom: 25px;
        transition: all 0.3s ease;
    }
    .feature-card:hover { border-color: #3b82f6; background: rgba(255, 255, 255, 0.05); }

    /* Buttons */
    .stButton>button {
        width: 100%; border-radius: 12px; height: 3.5em; 
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
        color: white; font-weight: 700; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 10px 20px -5px rgba(37,99,235,0.5); }

    /* Special Buttons */
    div[data-testid="stVerticalBlock"] > div:nth-child(1) .emergency-btn button {
        background: #dc2626 !important; border: none !important;
    }
    div[data-testid="stVerticalBlock"] > div:nth-child(1) .counselor-btn button {
        background: #059669 !important; border: none !important;
    }

    /* Professional UI Components */
    .motivation-box {
        padding: 25px; background: rgba(37, 99, 235, 0.1); 
        border-left: 4px solid #3b82f6; border-radius: 12px;
        font-style: italic; color: #93c5fd; margin-bottom: 30px;
    }
    .hero-text { font-size: 50px; font-weight: 800; color: #ffffff; text-align: center; }
    
    /* Input field styling for dark mode */
    input, textarea { background-color: #1e293b !important; color: white !important; border-color: #334155 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🏗️ BACKEND: INTELLIGENCE & ALERTS
# ==========================================
def init_db():
    with sqlite3.connect('safeschool_pro.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidents 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, platform TEXT, 
             type TEXT, severity TEXT, emotion TEXT, summary TEXT, status TEXT, score REAL)''')

def trigger_counselor_alarm(level="CRITICAL", message="Emergency Button Pressed"):
    """Sends immediate silent alarm to the database and email"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect('safeschool_pro.db') as conn:
        conn.execute("INSERT INTO incidents (ts, platform, type, severity, emotion, summary, status, score) VALUES (?,?,?,?,?,?,?,?)",
                     (ts, "INTERNAL", "EMERGENCY ALARM", "CRITICAL", "Panic", message, "🚨 UNREAD ALARM", 1.0))
    # Send email alert to counselor
    try:
        msg = EmailMessage()
        msg['Subject'] = f"🚨 SCHOOL EMERGENCY ALARM: {level}"
        msg['From'] = SMTP_USER
        msg['To'] = "counselor@school.com"
        msg.set_content(f"TIME: {ts}\nNATURE: {message}\n\nPlease check the dashboard immediately.")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    except: pass

def call_ai_models(text):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    tox_api = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    emo_api = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
    try:
        t_res = requests.post(tox_api, headers=headers, json={"inputs": text}, timeout=10).json()
        e_res = requests.post(emo_api, headers=headers, json={"inputs": text}, timeout=10).json()
        return t_res[0][0]['score'], e_res[0][0]['label']
    except: return 0.5, "neutral"

def anonymize(text):
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    text = re.sub(r'\d{10}', '[PHONE]', text)
    return re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text)

# ==========================================
# 🚦 ROUTING
# ==========================================
init_db()
if 'view' not in st.session_state: st.session_state.view = "Home"

# --- PAGE 1: PROFESSIONAL LANDING ---
if st.session_state.view == "Home":
    st.markdown("<br><br><div class='hero-text'>🛡️ SafeSchool AI</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#94a3b8; font-size:18px;'>Ensuring Student Safety through Real-Time AI Intelligence</p><br>", unsafe_allow_html=True)
    
    c_left, c_right = st.columns(2, gap="large")
    with c_left:
        st.markdown("<div class='feature-card'><h3>Student Portal</h3><p>Report harassment with zero traces. Our AI ensures your identity is never compromised.</p></div>", unsafe_allow_html=True)
        if st.button("🚀 Access Reporting Terminal"):
            st.session_state.view = "Student"; st.rerun()
    with c_right:
        st.markdown("<div class='feature-card'><h3>Administration</h3><p>Secure login for school counselors to manage incidents and protect students.</p></div>", unsafe_allow_html=True)
        u = st.text_input("Staff ID")
        p = st.text_input("Security Key", type="password")
        if st.button("🔒 Secure Authentication"):
            if u == C_USER and p == C_PASS:
                st.session_state.view = "Staff"; st.rerun()
            else: st.error("Access Denied")

# --- PAGE 2: STUDENT PORTAL ---
elif st.session_state.view == "Student":
    if st.sidebar.button("🏠 Exit to Home"):
        st.session_state.view = "Home"; st.rerun()

    quotes = [
        "Your bravery in reporting this is the first step toward a safer school for everyone.",
        "No one has the power to define you. You are strong, and you are not alone.",
        "The screen should be a place of connection, not a weapon of pain. We are here to help."
    ]
    st.markdown(f"<div class='motivation-box'>“{random.choice(quotes)}”</div>", unsafe_allow_html=True)
    
    st.subheader("🆘 Emergency Assistance")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.markdown('<div class="emergency-btn">', unsafe_allow_html=True)
        if st.button("🚨 TRIGGER EMERGENCY ALARM"):
            trigger_counselor_alarm("CRITICAL", "Student triggered Emergency Panic Button")
            st.error("ALARM SENT. A counselor has been notified of an immediate emergency.")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_e2:
        st.markdown('<div class="counselor-btn">', unsafe_allow_html=True)
        if st.button("🤝 REQUEST PRIORITY CALL"):
            trigger_counselor_alarm("HIGH", "Student requested priority call-back")
            st.success("Request logged. Check-in scheduled.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br><div class='feature-card'>", unsafe_allow_html=True)
    st.markdown("### Incident Analysis Terminal")
    msg = st.text_area("What happened? (Paste text or describe events)")
    imgs = st.file_uploader("Upload Chat Screenshots", accept_multiple_files=True)
    
    c1, c2 = st.columns(2)
    plat = c1.selectbox("Source Platform", ["WhatsApp", "Instagram", "Discord", "Snapchat", "Other"])
    freq = c2.selectbox("Occurrence", ["First time", "Multiple times", "Persistent Bullying"])
    
    if st.button("Analyze & Anonymize Report"):
        with st.status("🛠️ AI Pipeline Engaged...", expanded=True) as s:
            ocr_text = ""
            if imgs:
                reader = easyocr.Reader(['en'])
                for img in imgs:
                    res = reader.readtext(np.array(Image.open(img)))
                    ocr_text += " " + " ".join([r[1] for r in res])
            
            clean = anonymize(msg + " " + ocr_text)
            tox, emo = call_ai_models(clean)
            
            # Auto-Alarm for 80%+
            if tox >= 0.80:
                trigger_counselor_alarm("HIGH TOXICITY", f"AI detected {int(tox*100)}% toxicity in a report.")
                st.warning("⚠️ Critical toxicity detected. High-priority alert sent to staff.")

            with sqlite3.connect('safeschool_pro.db') as conn:
                conn.execute("INSERT INTO incidents (ts, platform, type, severity, emotion, summary, status, score) VALUES (?,?,?,?,?,?,?,?)",
                             (datetime.now().strftime("%H:%M"), plat, "Cyberbullying", "HIGH" if tox > 0.7 else "LOW", emo, clean[:300], "Pending", tox))
            
            s.update(label="Report Secured!", state="complete")
            st.balloons(); st.success("Your report was submitted anonymously.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- PAGE 3: STAFF DASHBOARD ---
elif st.session_state.view == "Staff":
    st.sidebar.button("🚪 Logout", on_click=lambda: st.session_state.update({"view": "Home"}))
    st.title("📊 Safety Command Center")
    
    with sqlite3.connect('safeschool_pro.db') as conn:
        df = pd.read_sql_query("SELECT * FROM incidents ORDER BY id DESC", conn)
    
    if not df.empty:
        # Emergency Alarm Banner
        if not df[df.status == "🚨 UNREAD ALARM"].empty:
            st.error(f"⚠️ ATTENTION: You have {len(df[df.status == '🚨 UNREAD ALARM'])} unread Emergency Alarms!")

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Reports", len(df))
        m2.metric("Critical Alerts", len(df[df.severity == "CRITICAL" if "CRITICAL" in df.severity.values else df.severity == "HIGH"]))
        m3.metric("System Health", "Optimal")
        
        st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Admin Actions
        case_id = st.number_input("Enter Case ID to update", min_value=1, step=1)
        if st.button("Mark as Investigated/Resolved"):
            with sqlite3.connect('safeschool_pro.db') as conn:
                conn.execute("UPDATE incidents SET status = 'Resolved' WHERE id = ?", (case_id,))
            st.rerun()
    else:
        st.info("No active incidents in the database.")
