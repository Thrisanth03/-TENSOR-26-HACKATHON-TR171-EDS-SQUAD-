import streamlit as st
from transformers import pipeline
import re

st.set_page_config(page_title="Cyberbullying Analyzer", layout="centered")

st.title("🚨 Cyberbullying Incident Analyzer")

# ---------------- LOAD MODELS (CACHED) ----------------
@st.cache_resource
def load_models():
    classifier = pipeline("text-classification", model="unitary/toxic-bert")
    emotion_model = pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base"
    )
    summarizer = pipeline(
        "summarization",
        model="sshleifer/distilbart-cnn-12-6"
    )
    return classifier, emotion_model, summarizer

classifier, emotion_model, summarizer = load_models()

# ---------------- INPUT ----------------
text = st.text_area("Enter Report")
frequency = st.slider("Frequency", 1, 10, 1)
duration = st.slider("Duration (days)", 1, 30, 1)

# ---------------- FUNCTIONS ----------------
def mask_pii(text):
    text = re.sub(r'\b[A-Z][a-z]{2,}\b', '[NAME]', text)
    text = re.sub(r'\b\d{10}\b', '[PHONE]', text)
    return text

def classify_type(text):
    text = text.lower()
    if any(w in text for w in ["kill", "hurt", "beat", "threat"]):
        return "Threats"
    elif any(w in text for w in ["ignore", "exclude"]):
        return "Social Exclusion"
    elif any(w in text for w in ["stupid", "idiot", "loser", "dumb"]):
        return "Verbal"
    elif any(w in text for w in ["touch", "sexual"]):
        return "Sexual"
    return "Verbal"

def calculate_severity(toxicity, frequency, duration):
    frequency = min(frequency / 10, 1)
    duration = min(duration / 30, 1)
    score = (toxicity * 0.5) + (frequency * 0.3) + (duration * 0.2)

    if score > 0.7:
        return "HIGH"
    elif score > 0.4:
        return "MEDIUM"
    return "LOW"

def detect_pattern(frequency, duration):
    if frequency > 3 and duration > 5:
        return "Repeated bullying detected"
    return "No strong pattern"

def recommend_action(b_type, severity):
    if b_type == "Sexual":
        return "Mandatory escalation (Protocol D)"
    if b_type == "Threats" and severity == "HIGH":
        return "Immediate escalation (Protocol C)"
    if severity == "MEDIUM":
        return "Counselor session (Protocol B)"
    return "Monitor (Protocol A)"

def simple_summary(text):
    return text[:150]  # fallback

# ---------------- ANALYZE ----------------
if st.button("Analyze"):
    if text.strip() == "":
        st.warning("Please enter a report")
    else:
        try:
            clean = mask_pii(text)

            # Toxicity
            result = classifier(clean)[0]
            toxicity = result['score']

            # Type + Severity
            b_type = classify_type(clean)
            severity = calculate_severity(toxicity, frequency, duration)

            # Emotion
            emotion = emotion_model(clean)[0]['label']

            # Pattern
            pattern = detect_pattern(frequency, duration)

            # Summary (safe)
            try:
                summary = summarizer(
                    clean,
                    max_length=60,
                    min_length=20,
                    do_sample=False
                )[0]['summary_text']
            except:
                summary = simple_summary(clean)

            # Action
            action = recommend_action(b_type, severity)

            # ---------------- OUTPUT ----------------
            st.subheader("Results")

            if severity == "HIGH":
                st.error("HIGH RISK 🚨")
            elif severity == "MEDIUM":
                st.warning("MEDIUM RISK ⚠️")
            else:
                st.success("LOW RISK ✅")

            st.write("**Type:**", b_type)
            st.write("**Emotion:**", emotion)
            st.write("**Pattern:**", pattern)
            st.write("**Summary:**", summary)
            st.write("**Action:**", action)

        except Exception as e:
            st.error("Something went wrong. Try again.")
            st.text(str(e))
