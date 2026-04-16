import streamlit as st
import requests
import os

st.set_page_config(page_title="SafeReport", layout="wide", page_icon="🛡️")

# ── Config ─────────────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "https://your-backend.onrender.com")
API = f"{BACKEND_URL}/analyze"

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: #f8f8f5; }
.block-container { max-width: 720px; }
.metric-label { font-size: 12px !important; color: #888 !important; }
</style>
""", unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────────────
tab_student, tab_dashboard = st.tabs(["📝 Report Incident", "📊 Counselor Dashboard"])


# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT TAB
# ═══════════════════════════════════════════════════════════════════════════════
with tab_student:
    st.markdown("### Describe what happened")
    st.caption("Your identity is never stored. All reports are fully anonymous.")

    text = st.text_area("Incident description", height=140,
                        placeholder="Describe what happened in your own words...")

    col1, col2, col3 = st.columns(3)
    with col1:
        platform = st.selectbox("Platform", ["WhatsApp", "Instagram", "School App", "Other"])
    with col2:
        frequency = st.selectbox("How often?", ["once", "few", "repeated"],
                                 format_func=lambda x: {"once":"Once","few":"A few times","repeated":"Repeatedly"}[x])
    with col3:
        duration = st.selectbox("For how long?", ["days", "weeks", "months"])

    if st.button("🔍 Analyze Report", type="primary"):
        if not text.strip():
            st.warning("Please describe the incident before submitting.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    r = requests.post(API, json={
                        "text": text,
                        "platform": platform,
                        "frequency": frequency,
                        "duration": duration,
                    }, timeout=15)
                    r.raise_for_status()
                    result = r.json()
                except Exception as e:
                    st.error(f"Could not reach backend: {e}")
                    result = None

            if result:
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("Type", result["type"])
                c2.metric("Severity", result["severity"])
                c3.metric("Toxicity score", f"{result.get('toxicity', 0):.2f}")

                sev = result["severity"]
                if sev == "HIGH":
                    st.error("🚨 High-risk incident — counselor will be notified immediately.")
                elif sev == "MEDIUM":
                    st.warning("⚠️ This has been flagged for counselor review.")
                else:
                    st.success("✅ Report recorded. Our safety team will monitor this.")

                st.markdown("**Summary**")
                st.info(result["summary"])
                st.markdown("**Recommended action**")
                st.write(result["action"])

                st.caption("🔒 Your identity is protected. This report contains no personal information.")


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD TAB
# ═══════════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    st.markdown("### Incident Dashboard")

    # Stats
    try:
        stats = requests.get(f"{BACKEND_URL}/stats", timeout=8).json()
        s1, s2, s3 = st.columns(3)
        s1.metric("Total incidents", stats.get("total", 0))
        s2.metric("High severity", stats.get("high_severity", 0))
        s3.metric("Types tracked", len(stats.get("by_type", {})))
    except Exception:
        st.warning("Could not load stats — is the backend running?")

    st.divider()

    # Filters
    f1, f2 = st.columns(2)
    with f1:
        f_sev = st.selectbox("Filter by severity", ["All", "HIGH", "MEDIUM", "LOW"])
    with f2:
        f_type = st.selectbox("Filter by type",
                              ["All", "Threat", "Verbal Abuse", "Sexual Harassment",
                               "Social Exclusion", "General"])

    if st.button("Load incidents"):
        params = {}
        if f_sev != "All":   params["severity"] = f_sev
        if f_type != "All":  params["btype"]    = f_type

        try:
            rows = requests.get(f"{BACKEND_URL}/incidents", params=params, timeout=8).json()
        except Exception as e:
            st.error(f"Backend error: {e}")
            rows = []

        if not rows:
            st.info("No incidents found for these filters.")
        else:
            import pandas as pd
            df = pd.DataFrame(rows)[["id","timestamp","platform","type","severity","summary","action"]]
            df.columns = ["ID","Timestamp","Platform","Type","Severity","Summary","Action"]
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Detail view
            ids = [r["id"] for r in rows]
            sel = st.selectbox("View incident detail", ids)
            if sel:
                inc = next(r for r in rows if r["id"] == sel)
                with st.expander(f"Incident #{sel}", expanded=True):
                    st.write(f"**Type:** {inc['type']}  |  **Severity:** {inc['severity']}")
                    st.write(f"**Platform:** {inc.get('platform','—')}  |  **Timestamp:** {inc['timestamp']}")
                    st.info(inc["summary"])
                    st.write(f"**Recommended action:** {inc['action']}")
