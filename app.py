import streamlit as st
from transformers import pipeline
import pandas as pd
import re
import os

# Fix tokenizer warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="AI Bullying Detection System",
    page_icon="🛡️",
    layout="centered"
)

# -----------------------------
# LOAD MODELS (LIGHTWEIGHT)
# -----------------------------
@st.cache_resource
def load_models():
    classifier = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )

    summarizer = pipeline(
        "text-generation",
        model="google/flan-t5-small"   # ⚡ faster + deploy-safe
    )

    return classifier, summarizer

classifier, summarizer = load_models()

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("⚙️ Settings")
st.sidebar.write("AI-powered bullying detection system")

frequency = st.sidebar.slider("Frequency", 1, 10, 1)
duration = st.sidebar.slider("Duration", 1, 10, 1)

# -----------------------------
# FUNCTIONS
# -----------------------------
def mask_pii(text):
    text = re.sub(r'\b[A-Z][a-z]{2,}\b', '[NAME]', text)
    text = re.sub(r'\b\d{10}\b', '[PHONE]', text)
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    return text

def classify_type(text):
    text = text.lower()

    if any(w in text for w in ["kill", "hurt", "beat", "threat"]):
        return "Threats"
    elif any(w in text for w in ["ignore", "exclude", "left out"]):
        return "Social Exclusion"
    elif any(w in text for w in ["touch", "body", "sexual"]):
        return "Sexual"
    elif any(w in text for w in ["ugly", "stupid", "loser", "idiot"]):
        return "Verbal"

    return "Verbal"

def calculate_severity(toxicity_score, frequency, duration):
    score = (toxicity_score * 0.5) + (frequency * 0.3) + (duration * 0.2)

    if score > 0.7:
        return "HIGH"
    elif score > 0.4:
        return "MEDIUM"
    return "LOW"

def recommend_action(b_type, severity):
    if b_type == "Sexual":
        return "Mandatory escalation (Protocol Section D)"
    if b_type == "Threats" and severity == "HIGH":
        return "Immediate escalation (Protocol Section C)"
    if severity == "MEDIUM":
        return "Counselor session (Protocol Section B)"
    return "Monitor situation (Protocol Section A)"

def generate_summary(text):
    try:
        prompt = f"Summarize this bullying report:\n{text}"
        result = summarizer(prompt, max_length=80, do_sample=False)
        return result[0]['generated_text']
    except:
        return "Summary not available"

# -----------------------------
# UI MAIN
# -----------------------------
st.title("🛡️ AI Bullying Detection System")
st.markdown("### Analyze reports using AI")

text = st.text_area("📝 Enter Complaint / Report")

if st.button("🔍 Analyze Report"):

    if text.strip() == "":
        st.warning("Please enter some text")
    else:
        clean_text = mask_pii(text)

        result = classifier(clean_text)[0]
        toxicity_score = result['score'] if result['label'] == 'NEGATIVE' else 0

        b_type = classify_type(clean_text)
        severity = calculate_severity(toxicity_score, frequency, duration)
        summary = generate_summary(clean_text)
        action = recommend_action(b_type, severity)

        # -----------------------------
        # DISPLAY RESULTS
        # -----------------------------
        st.subheader("📊 Analysis Results")

        st.write("**Masked Text:**", clean_text)
        st.write("**Toxicity Score:**", round(toxicity_score, 2))
        st.write("**Bullying Type:**", b_type)

        # Severity color
        if severity == "HIGH":
            st.error(f"🚨 Severity: {severity}")
        elif severity == "MEDIUM":
            st.warning(f"⚠️ Severity: {severity}")
        else:
            st.success(f"✅ Severity: {severity}")

        st.write("**Summary:**", summary)
        st.write("**Recommended Action:**", action)

        # -----------------------------
        # DOWNLOAD REPORT
        # -----------------------------
        data = {
            "Text": [text],
            "Masked": [clean_text],
            "Type": [b_type],
            "Severity": [severity],
            "Action": [action]
        }

        df = pd.DataFrame(data)

        st.download_button(
            label="📥 Download Report (CSV)",
            data=df.to_csv(index=False),
            file_name="bullying_report.csv",
            mime="text/csv"
        )
