import streamlit as st
import requests

st.set_page_config(page_title="Cyberbullying AI", layout="wide")

st.title("🚨 Cyberbullying Incident Analyzer")

API_URL = "https://your-backend-url/analyze"  # 🔁 replace after deployment

# ---------------- INPUT ----------------
text = st.text_area("📝 Enter Report")
frequency = st.slider("Frequency", 1, 10, 1)
duration = st.selectbox("Duration", ["days", "weeks", "months"])

# ---------------- ANALYZE ----------------
if st.button("🔍 Analyze"):
    if text.strip() == "":
        st.warning("Please enter a report")
    else:
        with st.spinner("Analyzing..."):
            try:
                response = requests.post(
                    API_URL,
                    json={
                        "text": text,
                        "frequency": frequency,
                        "duration": duration
                    }
                )

                result = response.json()

                # ---------------- UI ----------------
                col1, col2, col3 = st.columns(3)

                col1.metric("Severity", result["severity"])
                col2.metric("Toxicity", round(result["toxicity"], 2))
                col3.metric("Type", result["type"])

                if result["severity"] == "HIGH":
                    st.error("🚨 High Risk Detected")
                elif result["severity"] == "MEDIUM":
                    st.warning("⚠️ Medium Risk")
                else:
                    st.success("✅ Low Risk")

                st.write("### 🧾 Summary")
                st.info(result["summary"])

                st.write("### 🎯 Recommended Action")
                st.write(result["action"])

            except:
                st.error("Backend not reachable")
