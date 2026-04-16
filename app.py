from transformers import pipeline
import re

# -----------------------------
# LOAD MODELS
# -----------------------------
print("Loading models...")

classifier = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

# ✅ FIXED summarizer (works in your environment)
summarizer = pipeline(
    "text-generation",
    model="google/flan-t5-base"
)

print("Models loaded!\n")

# -----------------------------
# 1. PII MASKING
# -----------------------------
def mask_pii(text):
    text = re.sub(r'\b[A-Z][a-z]{2,}\b', '[NAME]', text)
    text = re.sub(r'\b\d{10}\b', '[PHONE]', text)
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    return text

# -----------------------------
# 2. BULLYING TYPE
# -----------------------------
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

# -----------------------------
# 3. SEVERITY
# -----------------------------
def calculate_severity(toxicity_score, frequency, duration):
    score = (toxicity_score * 0.5) + (frequency * 0.3) + (duration * 0.2)

    if score > 0.7:
        return "HIGH"
    elif score > 0.4:
        return "MEDIUM"
    return "LOW"

# -----------------------------
# 4. ACTION
# -----------------------------
def recommend_action(b_type, severity):

    if b_type == "Sexual":
        return "Mandatory escalation (Protocol Section D)"

    if b_type == "Threats" and severity == "HIGH":
        return "Immediate escalation (Protocol Section C)"

    if severity == "MEDIUM":
        return "Counselor session (Protocol Section B)"

    return "Monitor situation (Protocol Section A)"

# -----------------------------
# 5. SUMMARY (FLAN-T5 BASED)
# -----------------------------
def generate_summary(text):
    try:
        prompt = f"Summarize this bullying report clearly:\n{text}"

        result = summarizer(
            prompt,
            max_length=100,
            do_sample=False
        )

        return result[0]['generated_text']
    except:
        return "Summary not available"

# -----------------------------
# MAIN PIPELINE
# -----------------------------
def analyze_report(text, frequency=1, duration=1):

    # Step 1: Mask PII
    clean_text = mask_pii(text)

    # Step 2: Toxicity
    result = classifier(clean_text)[0]
    toxicity_score = result['score'] if result['label'] == 'NEGATIVE' else 0

    # Step 3: Type
    b_type = classify_type(clean_text)

    # Step 4: Severity
    severity = calculate_severity(toxicity_score, frequency, duration)

    # Step 5: Summary
    summary = generate_summary(clean_text)

    # Step 6: Action
    action = recommend_action(b_type, severity)

    return {
        "Masked_Text": clean_text,
        "Toxicity_Score": round(toxicity_score, 2),
        "Bullying_Type": b_type,
        "Severity": severity,
        "Summary": summary,
        "Recommended_Action": action
    }

# -----------------------------
# TEST RUN
# -----------------------------
text = "Rahul keeps calling me stupid and threatening to beat me every day. Contact me at 9876543210."

output = analyze_report(text, frequency=5, duration=7)

print("\n--- ANALYSIS RESULT ---\n")
for k, v in output.items():
    print(f"{k}: {v}")