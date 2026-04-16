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
# 🔑 INBUILT CONFIGURATION & BRANDING
# ==========================================
HF_API_KEY = "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"  # Use your Hugging Face Token
C_USER, C_PASS = "admin", "SafeSchool2026"

# Email Configuration (SMTP)
SMTP_USER = "yourschool@gmail.com"
SMTP_PASS = "xxxx xxxx xxxx xxxx" # Gmail App Password
COUNSELOR_EMAIL = "safety@school.com"

# --- THEME & CSS ---
st.set_page_config(page_title="SafeSchool AI | Incident Response", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .report-card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #edf2f7; }
    .header-style { color: #1e293b; font-weight: 800; }
    .stMetric { background: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-badge { padding: 5px 12px; border-radius: 15px; font-weight: bold; font-size: 0.8rem; }
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
    """Deep Anonymization Engine"""
    text = re.sub(r'\S+@\S+', '[REDACTED_EMAIL]', text) # Emails
    text = re.sub(r'\+?\d{10,12}', '[REDACTED_PHONE]', text) # Phones
    text = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[REDACTED_NAME]', text) # Full Names
    return text

# ==========================================
# 🧠 AI ENGINE: CLOUD ANALYSIS
# ==========================================
def query_ai(text):
    """Dual-Task AI: Toxicity & Emotion Extraction"""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # Task 1: Toxicity Score
    tox_url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    # Task 2: Emotion Recognition
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
    if severity == "HIGH": return "🚨 Immediate Intervention: Lockdown platforms and notify parents."
    if severity == "MEDIUM": return "🤝 Counselor Session: Scheduled mandatory mediation."
    return "📝 Active Monitoring: Log incident and observe future interactions."

# ==========================================
# 📧 NOTIFICATION ENGINE
# ==========================================
def trigger_alert(data):
    try:
        msg = EmailMessage()
        msg['Subject'] = f"🚨 URGENT: High Severity {data['type']} Alert"
        msg['From'] = SMTP_USER
        msg['To'] = COUNSELOR_EMAIL
        content = f"""
        Priority Alert: High Severity Cyberbullying Detected
        ---------------------------------------------------
        Type: {data['type']}
        Emotion Detected: {data['emotion']}
        Platform: {data['platform']}
        
        Summary: {data['summary']}
        
        AI Recommended Action: {data['action']}
        Timestamp: {data['ts']}
        """
        msg.set_content(content)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    except: pass

# ==========================================
# 🖥️ FRONTEND INTERFACE
# ==========================================
init_db()

if 'session_auth' not in st.session_state:
    st.session_state.session_auth = False
    st.session_state.user_role = None

if not st.session_state.session_auth:
    # --- LOGIN PORTAL ---
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.image("https://cdn-icons-png.flaticon.com/512/3655/3655610.png", width=120)
        st.markdown("<h1 class='header-style'>SafeSchool AI Gateway</h1>", unsafe_allow_html=True)
        st.write("Ensuring a safe digital environment for every student.")
    
    with col_r:
        portal = st.tabs(["Student (Anonymous)", "Counselor Login"])
        
        with portal[0]:
            st.info("Submit reports without sharing your name, ID, or IP.")
            if st.button("Access Anonymous Reporting", use_container_width=True):
                st.session_state.user_role = "student"; st.session_state.session_auth = True; st.rerun()
                
        with portal[1]:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Authorize Access", use_container_width=True):
                if u == C_USER and p == C_PASS:
                    st.session_state.user_role = "counselor"; st.session_state.session_auth = True; st.rerun()
                else: st.error("Invalid Security Credentials")

else:
    # --- AUTHENTICATED NAVBAR ---
    st.sidebar.title("🛡️ SafeSchool Navigation")
    if st.sidebar.button("System Logout", use_container_width=True):
        st.session_state.session_auth = False; st.rerun()

    if st.session_state.user_role == "student":
        st.markdown("<h2 class='header-style'>Incident Reporting Form</h2>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<div class='report-card'>", unsafe_allow_html=True)
            
            # Step 1: Input
            c1, c2 = st.columns(2)
            u_text = c1.text_area("Describe the situation", placeholder="What was said or done?")
            u_imgs = c2.file_uploader("Upload Screenshots (Optional)", accept_multiple_files=True)
            
            c3, c4, c5 = st.columns(3)
            plat = c3.selectbox("Platform", ["WhatsApp", "Instagram", "Snapchat", "Discord", "Other"])
            freq = c4.selectbox("Frequency", ["Once", "Few times (2-4)", "Repeatedly (5+)"])
            dur = c5.selectbox("Duration", ["Days", "Weeks", "Months"])
            
            if st.button("Process & Submit Report", type="primary", use_container_width=True):
                with st.status("Initializing AI Pipeline...", expanded=True) as status:
                    # Step 2: OCR
                    status.write("Running OCR Engine...")
                    ocr_merged = ""
                    if u_imgs:
                        reader = easyocr.Reader(['en'])
                        for img in u_imgs:
                            res = reader.readtext(np.array(Image.open(img)))
                            ocr_merged += " " + " ".join([r[1] for r in res])
                    
                    # Step 3: Anonymization
                    status.write("Anonymizing Data...")
                    final_text = scrub_pii(u_text + " " + ocr_merged)
                    
                    # Step 4: AI Analysis
                    status.write("Calling Cloud AI Models...")
                    tox_score, emotion = query_ai(final_text)
                    
                    # Step 5: Severity Logic
                    status.write("Calculating Severity Score...")
                    itype = "Harassment"
                    if any(w in final_text.lower() for w in ["kill", "die", "hurt", "find you"]): itype = "Threat"
                    
                    # Severity calculation based on your parameters
                    sev = "LOW"
                    if tox_score > 0.8 or itype == "Threat" or freq == "Repeatedly (5+)" or dur == "Months":
                        sev = "HIGH"
                    elif tox_score > 0.4 or freq == "Few times (2-4)" or dur == "Weeks":
                        sev = "MEDIUM"
                    
                    recom = get_action_recommendation(sev, itype)
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Step 6: Database Storage
                    with sqlite3.connect('safeguard_vault.db') as conn:
                        conn.execute('''INSERT INTO incidents 
                            (ts, platform, type, severity, emotion, summary, action, status, toxicity) 
                            VALUES (?,?,?,?,?,?,?,?,?)''', 
                            (ts, plat, itype, sev, emotion, final_text[:500], recom, "Pending", tox_score))
                    
                    # Step 7: Alert
                    if sev == "HIGH":
                        trigger_alert({'type': itype, 'sev': sev, 'emotion': emotion, 'summary': final_text[:200], 'ts': ts, 'action': recom, 'platform': plat})
                    
                    status.update(label="Report Secured & Logged!", state="complete")
                    st.balloons()
                    st.success("Submission Successful. Your privacy is our priority.")
            
            st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.user_role == "counselor":
        st.markdown("<h2 class='header-style'>Counselor Command Center</h2>", unsafe_allow_html=True)
        
        with sqlite3.connect('safeguard_vault.db') as conn:
            df = pd.read_sql_query("SELECT * FROM incidents ORDER BY id DESC", conn)
        
        if not df.empty:
            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Cases", len(df))
            m2.metric("Critical Alerts", len(df[df.severity == "HIGH"]))
            m3.metric("Avg. Toxicity", f"{int(df.toxicity.mean()*100)}%")
            m4.metric("Top Emotion", df.emotion.mode()[0])
            
            st.write("---")
            
            # Filters
            f_col1, f_col2 = st.columns(2)
            f_sev = f_col1.multiselect("Filter by Severity", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"])
            f_plat = f_col2.multiselect("Filter by Platform", df.platform.unique(), default=df.platform.unique())
            
            filtered_df = df[(df.severity.isin(f_sev)) & (df.platform.isin(f_plat))]
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            
            # Resolution Tool
            st.write("### Case Management")
            case_id = st.selectbox("Select Case ID to Update", df.id.tolist())
            new_status = st.select_slider("Set Status", ["Pending", "In Review", "Resolved"])
            if st.button("Update Case Status"):
                with sqlite3.connect('safeguard_vault.db') as conn:
                    conn.execute("UPDATE incidents SET status = ? WHERE id = ?", (new_status, case_id))
                st.toast(f"Case #{case_id} updated to {new_status}!")
                st.rerun()
        else:
            st.info("System is monitoring. No incidents reported yet.")
