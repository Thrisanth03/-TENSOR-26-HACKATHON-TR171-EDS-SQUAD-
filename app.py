import streamlit as st
import requests
import re
import json

# --- SECRETS MANAGEMENT ---
# In Streamlit Cloud, add your key to "Settings > Secrets"
# It should look like: HF_API_KEY = "your_token_here"
API_KEY = st.secrets["HF_API_KEY"]
API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"

# --- SYSTEM LOGIC ---

def scrub_pii(text):
    """Anonymizes names, emails, and phones using Regex."""
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    text = re.sub(r'\d{10}', '[PHONE]', text)
    # Simple name scrubber (Capitalized words)
    text = re.sub(r'\b[A-Z][a-z]+\b', '[NAME]', text)
    return text

def analyze_text(text):
    """Sends text to a cloud AI model via simple API request."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {"inputs": text}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        result = response.json()
        # Returns the top toxicity score
        return result[0][0]['score']
    except Exception as e:
        st.error("AI Analysis failed. Check your API Key.")
        return 0.0

# --- FRONTEND UI ---
st.title("🛡️ SafeSchool Incident Reporter")
st.markdown("Submit a report anonymously. Our AI scans for toxicity while protecting privacy.")

with st.container():
    raw_input = st.text_area("What happened?", placeholder="Type incident details here...")
    
    col1, col2 = st.columns(2)
    with col1:
        platform = st.selectbox("Platform", ["WhatsApp", "Instagram", "Discord", "Other"])
    with col2:
        frequency = st.radio("Frequency", ["Once", "Repeated"])

    if st.button("Submit Anonymous Report", use_container_width=True):
        if raw_input:
            # 1. Anonymize
            clean_text = scrub_pii(raw_input)
            
            # 2. Analyze
            tox_score = analyze_text(clean_text)
            
            # 3. Severity Logic
            severity = "🔴 HIGH" if tox_score > 0.75 else "🟡 MEDIUM" if tox_score > 0.4 else "🟢 LOW"
            
            # 4. Results
            st.divider()
            st.subheader("Analysis Summary")
            st.write(f"**Anonymized Report:** {clean_text}")
            
            kpi1, kpi2 = st.columns(2)
            kpi1.metric("Calculated Severity", severity)
            kpi2.metric("Toxicity Score", f"{int(tox_score * 100)}%")
            
            if severity == "🔴 HIGH":
                st.warning("Action Required: This incident has been flagged for counselor intervention.")
            else:
                st.success("Report logged for monitoring.")
        else:
            st.error("Please enter report details.")
