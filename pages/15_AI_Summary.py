# pages/15_AI_Attrition_Summary.py
"""
AI Attrition Risk Summary — Powered by Google Gemini (FREE)
Analyses attendance + mood + tasks + tenure to predict who might resign
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import datetime

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

st.set_page_config(page_title="AI Attrition Summary", page_icon="🔮", layout="wide")
require_login(roles_allowed=["Admin", "HR", "Manager"])
show_role_badge()
logout_user()

st.title("🔮 AI Attrition Risk Analysis")
st.caption("Powered by **Google Gemini** — identifies employees at risk of resigning")

# ─────────────────────────────────────────────
# Sidebar — API Key
# ─────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### 🔑 Gemini API Key")
st.sidebar.markdown("""
**Get FREE key:**
1. 👉 [aistudio.google.com](https://aistudio.google.com)
2. Sign in with Gmail
3. **Get API Key** → Create → Copy
""")
api_key = st.sidebar.text_input("Paste Gemini Key", type="password",
                                 placeholder="AIzaSy...", key="attrition_key")
model_choice = st.sidebar.selectbox(
    "Model", ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"], key="att_model"
)

# ─────────────────────────────────────────────
# Load & compute risk scores
# ─────────────────────────────────────────────
@st.cache_data(ttl=120)
def compute_risk():
    try:
        emp   = db.fetch_employees()
        att   = db.fetch_attendance()
        mood  = db.fetch_mood_logs()
        tasks = db.fetch_tasks()
    except Exception:
        return pd.DataFrame()

    active = emp[emp["Status"] == "Active"].copy() if not emp.empty else pd.DataFrame()
    if active.empty:
        return pd.DataFrame()

    rows = []
    for _, e in active.iterrows():
        eid  = e["Emp_ID"]
        risk = 0
        flags = []

        # --- Tenure: <6 months or >5 years both risky ---
        try:
            join = pd.to_datetime(e["Join_Date"])
            months = (pd.Timestamp.today() - join).days / 30
            if months < 6:
                risk += 20
                flags.append("🆕 Very new (<6 months)")
            elif months > 60:
                risk += 15
                flags.append("🕰️ Long tenure (>5 years, stagnation risk)")
        except Exception:
            months = 0

        # --- Attendance: low = high risk ---
        emp_att = att[att["emp_id"] == eid] if not att.empty else pd.DataFrame()
        if not emp_att.empty:
            present = len(emp_att[emp_att["status"].isin(["Present", "Remote"])])
            att_rate = present / len(emp_att) * 100
            if att_rate < 60:
                risk += 30
                flags.append(f"❌ Very low attendance ({att_rate:.0f}%)")
            elif att_rate < 80:
                risk += 15
                flags.append(f"⚠️ Below average attendance ({att_rate:.0f}%)")
        else:
            att_rate = 0

        # --- Mood: stressed = high risk ---
        emp_mood = mood[mood["emp_id"] == eid] if not mood.empty else pd.DataFrame()
        avg_mood = 0
        if not emp_mood.empty:
            avg_mood = emp_mood["mood_score"].mean()
            stressed_count = len(emp_mood[emp_mood["mood_score"] < 13])
            if avg_mood < 13:
                risk += 25
                flags.append(f"😟 Consistently stressed (avg score {avg_mood:.1f})")
            elif avg_mood < 16:
                risk += 10
                flags.append(f"😐 Below average mood (avg {avg_mood:.1f})")
            if stressed_count >= 3:
                risk += 10
                flags.append(f"🔴 {stressed_count} stressed mood entries")

        # --- Tasks: many overdue = disengaged ---
        emp_tasks = tasks[tasks["emp_id"] == eid] if not tasks.empty else pd.DataFrame()
        overdue = 0
        if not emp_tasks.empty:
            try:
                emp_tasks = emp_tasks.copy()
                emp_tasks["due_dt"] = pd.to_datetime(emp_tasks["due_date"], errors="coerce")
                overdue = len(emp_tasks[
                    (emp_tasks["status"] != "Completed") &
                    (emp_tasks["due_dt"] < pd.Timestamp.today())
                ])
                if overdue >= 3:
                    risk += 20
                    flags.append(f"📋 {overdue} overdue tasks (disengagement signal)")
                elif overdue >= 1:
                    risk += 8
            except Exception:
                pass

        # --- Salary: below dept average = risky ---
        try:
            dept      = e["Department"]
            dept_avg  = active[active["Department"] == dept]["Salary"].mean()
            my_sal    = float(e["Salary"])
            if my_sal < dept_avg * 0.8:
                risk += 15
                flags.append(f"💸 Salary ₹{my_sal:,.0f} is 20%+ below dept avg ₹{dept_avg:,.0f}")
        except Exception:
            my_sal = dept_avg = 0

        risk = min(risk, 100)

        if risk >= 60:   level = "🔴 High"
        elif risk >= 35: level = "🟡 Medium"
        else:            level = "🟢 Low"

        rows.append({
            "Emp_ID":       eid,
            "Name":         e["Name"],
            "Department":   e["Department"],
            "Role":         e["Role"],
            "Tenure (mo)":  round(months, 1),
            "Att Rate %":   round(att_rate, 1),
            "Avg Mood":     round(avg_mood, 1),
            "Overdue Tasks":overdue,
            "Salary":       round(float(e["Salary"]), 0),
            "Risk Score":   risk,
            "Risk Level":   level,
            "Risk Flags":   "\n".join(flags) if flags else "✅ No major concerns",
        })

    return pd.DataFrame(rows).sort_values("Risk Score", ascending=False)


risk_df = compute_risk()

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────
if not risk_df.empty:
    high   = len(risk_df[risk_df["Risk Level"] == "🔴 High"])
    medium = len(risk_df[risk_df["Risk Level"] == "🟡 Medium"])
    low    = len(risk_df[risk_df["Risk Level"] == "🟢 Low"])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Employees Analysed", len(risk_df))
    k2.metric("🔴 High Risk",          high,   delta=f"{high/len(risk_df)*100:.0f}%", delta_color="inverse")
    k3.metric("🟡 Medium Risk",         medium)
    k4.metric("🟢 Low Risk",            low)
    st.divider()

# ─────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────
if not risk_df.empty:
    col1, col2 = st.columns(2)

    with col1:
        rc = risk_df["Risk Level"].value_counts().reset_index()
        rc.columns = ["Level", "Count"]
        fig1 = px.pie(rc, names="Level", values="Count", hole=0.45,
                      title="Risk Distribution",
                      color="Level",
                      color_discrete_map={"🔴 High":"#ef4444","🟡 Medium":"#f59e0b","🟢 Low":"#22c55e"})
        fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=320)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        top20 = risk_df.head(20)
        fig2  = px.bar(top20, x="Risk Score", y="Name", orientation="h",
                       text="Risk Score", title="Top 20 At-Risk Employees",
                       color="Risk Score",
                       color_continuous_scale=["#22c55e","#f59e0b","#ef4444"],
                       range_color=[0, 100])
        fig2.update_traces(textposition="outside")
        fig2.update_layout(
            xaxis=dict(range=[0, 115]),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=320, coloraxis_showscale=False
        )
        st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────
# Full Risk Table
# ─────────────────────────────────────────────
st.subheader("📋 Full Attrition Risk Table")

if not risk_df.empty:
    f1, f2 = st.columns(2)
    f_level = f1.selectbox("Filter by Risk", ["All", "🔴 High", "🟡 Medium", "🟢 Low"])
    f_dept  = f2.selectbox("Filter by Dept",  ["All"] + sorted(risk_df["Department"].unique()))

    show = risk_df.copy()
    if f_level != "All": show = show[show["Risk Level"]   == f_level]
    if f_dept  != "All": show = show[show["Department"]   == f_dept]

    st.dataframe(
        show[["Name","Department","Role","Risk Score","Risk Level",
              "Att Rate %","Avg Mood","Overdue Tasks","Tenure (mo)","Risk Flags"]],
        use_container_width=True, height=380
    )

    csv = show.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Export Risk Table CSV", csv, "attrition_risk.csv", "text/csv")

st.divider()

# ─────────────────────────────────────────────
# Gemini AI Analysis
# ─────────────────────────────────────────────
st.subheader("🤖 AI Retention Recommendations")

if not api_key:
    st.info("""
    **Paste your free Gemini API key in the sidebar** to get AI-powered retention recommendations.

    👉 Get free key at [aistudio.google.com](https://aistudio.google.com) — takes 2 minutes, no credit card.
    """)
else:
    if not risk_df.empty:
        # Summarise top at-risk for AI prompt
        high_risk = risk_df[risk_df["Risk Level"] == "🔴 High"].head(10)
        summary_rows = []
        for _, r in high_risk.iterrows():
            summary_rows.append(
                f"- {r['Name']} ({r['Department']}, {r['Role']}): "
                f"Risk={r['Risk Score']}, Flags: {r['Risk Flags'].replace(chr(10), '; ')}"
            )
        high_risk_text = "\n".join(summary_rows) if summary_rows else "No high risk employees found."

        total_stats = (
            f"Total active employees: {len(risk_df)}\n"
            f"High risk: {high} | Medium: {medium} | Low: {low}\n"
            f"Avg attendance rate: {risk_df['Att Rate %'].mean():.1f}%\n"
            f"Avg mood score: {risk_df['Avg Mood'].mean():.1f}/25\n"
            f"Avg risk score: {risk_df['Risk Score'].mean():.1f}/100"
        )

        if st.button("🔮 Generate AI Retention Report", type="primary"):
            prompt = f"""You are an expert HR consultant analysing attrition risk for an Indian company.

WORKFORCE OVERVIEW:
{total_stats}

TOP HIGH-RISK EMPLOYEES:
{high_risk_text}

Please provide:
1. **Overall attrition risk assessment** (2-3 sentences)
2. **Top 3 root causes** driving the risk
3. **Specific retention strategies** for the high-risk employees listed above (be specific — mention names, departments)
4. **Immediate actions** HR should take in the next 30 days
5. **Long-term recommendations** (3-6 months)

Be specific, practical, and use Indian HR context. Format with clear headings."""

            try:
                url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{model_choice}:generateContent?key={api_key}")
                resp = requests.post(url, json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2500}
                }, timeout=45)

                if resp.status_code == 200:
                    ai_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    st.markdown(ai_text)

                    st.download_button(
                        "📥 Download AI Report",
                        ai_text.encode("utf-8"),
                        f"attrition_ai_report_{datetime.date.today()}.txt",
                        "text/plain"
                    )
                elif resp.status_code == 429:
                    st.warning("⚠️ Rate limit hit. Wait 1 minute and try again.")
                elif resp.status_code == 403:
                    st.error("❌ Invalid API key. Check your key at aistudio.google.com")
                else:
                    st.error(f"API error {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("No employee data available to analyse.")