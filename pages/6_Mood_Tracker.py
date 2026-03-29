# pages/6_Mood_Tracker.py
"""
Employee Mood Tracker — Workforce Intelligence System
- Consistent sidebar
- Plotly interactive charts with hover
- Survey with visual score display
- History table with filter
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user

st.set_page_config(page_title="Mood Tracker", page_icon="😊", layout="wide")
require_login()
show_role_badge()
logout_user()

role     = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "unknown")

st.title("😊 Employee Mood Tracker")

# ─────────────────────────────────────────────
# Load Employees
# ─────────────────────────────────────────────
try:
    employees_df = db.fetch_employees()
    employees_df = employees_df[employees_df["Status"] == "Active"]
except Exception:
    employees_df = pd.DataFrame(columns=["Emp_ID","Name","Status"])

if employees_df.empty:
    st.info("No active employee data available.")
    st.stop()

# Role-based: employees only see themselves
if role not in ["Admin", "Manager", "HR"]:
    employees_df = employees_df[employees_df["Name"] == username]
    if employees_df.empty:
        st.warning("Your employee profile was not found. Contact HR.")
        st.stop()

emp_list   = (employees_df["Emp_ID"].astype(str) + " — " + employees_df["Name"]).tolist()
emp_choice = st.selectbox("👤 Select Employee", emp_list)
emp_id     = int(emp_choice.split(" — ")[0])
emp_name   = emp_choice.split(" — ")[1]

st.divider()

# ─────────────────────────────────────────────
# Mood Survey Form
# ─────────────────────────────────────────────
st.subheader(f"📝 Daily Mood Survey — {emp_name}")
st.caption("Rate each area from 1 (worst) to 5 (best). This helps HR understand team wellbeing.")

with st.form("mood_survey_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    q1 = col1.slider("😤 Stress Level (1=very stressed, 5=relaxed)",    1, 5, 3)
    q2 = col1.slider("😊 Work Satisfaction (1=unhappy, 5=very happy)",  1, 5, 3)
    q3 = col2.slider("🔥 Motivation Level (1=unmotivated, 5=driven)",   1, 5, 3)
    q4 = col2.slider("⚖️ Work-Life Balance (1=poor, 5=excellent)",       1, 5, 3)
    q5 = st.slider( "🤝 Team Support (1=unsupported, 5=very supported)", 1, 5, 3)

    remarks = st.text_input("💬 Optional remarks or comments", placeholder="Anything you'd like to share...")
    submit  = st.form_submit_button("✅ Submit Mood Survey", use_container_width=True, type="primary")

    if submit:
        total_score = q1 + q2 + q3 + q4 + q5

        if total_score >= 20:   mood_label = "Happy"
        elif total_score >= 13: mood_label = "Neutral"
        else:                   mood_label = "Stressed"

        emoji_map  = {"Happy": "😊", "Neutral": "😐", "Stressed": "😟"}
        color_map  = {"Happy": "#22c55e", "Neutral": "#f59e0b", "Stressed": "#ef4444"}
        emoji      = emoji_map[mood_label]
        color      = color_map[mood_label]

        try:
            db.add_mood_entry(
                emp_id=emp_id,
                mood_score=int(total_score),
                remarks=f"{mood_label} | {remarks}" if remarks else mood_label
            )

            st.markdown(
                f"""<div style='background:{color}22; border-left:5px solid {color};
                     border-radius:8px; padding:20px; margin-top:10px;'>
                    <h3 style='color:{color}; margin:0;'>{emoji} Mood Recorded: {mood_label}</h3>
                    <p style='margin:6px 0 0; color:#555;'>Score: <b>{total_score}/25</b> — 
                    {'Great job keeping positive! 🌟' if mood_label == 'Happy' 
                     else 'Hang in there, things will get better! 💪' if mood_label == 'Neutral'
                     else 'We noticed you might be having a tough time. HR is here to help. 🤝'}
                    </p></div>""",
                unsafe_allow_html=True
            )
            st.rerun()

        except Exception as e:
            st.error("❌ Failed to save mood survey.")
            st.exception(e)

st.divider()

# ─────────────────────────────────────────────
# Load Mood History
# ─────────────────────────────────────────────
try:
    mood_df = db.fetch_mood_logs()
except Exception:
    mood_df = pd.DataFrame(columns=["emp_id","mood_score","remarks","log_date"])

if mood_df.empty:
    st.info("No mood survey data available yet.")
    st.stop()

emp_map_full = employees_df.set_index("Emp_ID")["Name"].to_dict()

# Load ALL employees for mapping (not just active filter above)
try:
    all_emp = db.fetch_employees()
    emp_map_full = all_emp.set_index("Emp_ID")["Name"].to_dict()
except Exception:
    pass

mood_df = mood_df.copy()
mood_df["Employee"] = mood_df["emp_id"].map(emp_map_full).fillna("Unknown")
mood_df["Score"]    = pd.to_numeric(mood_df["mood_score"], errors="coerce")
mood_df["Date"]     = pd.to_datetime(mood_df["log_date"],  errors="coerce")
mood_df["Mood"]     = mood_df["Score"].apply(
    lambda x: "Happy" if x >= 20 else ("Neutral" if x >= 13 else "Stressed")
)

# Role-based filtering: employees only see their own
if role not in ["Admin", "Manager", "HR"]:
    mood_df = mood_df[mood_df["Employee"] == username]

# ─────────────────────────────────────────────
# Quick Stats
# ─────────────────────────────────────────────
st.subheader("📊 Mood Overview")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Surveys",   len(mood_df))
k2.metric("😊 Happy",        len(mood_df[mood_df["Mood"] == "Happy"]))
k3.metric("😐 Neutral",      len(mood_df[mood_df["Mood"] == "Neutral"]))
k4.metric("😟 Stressed",     len(mood_df[mood_df["Mood"] == "Stressed"]))

# ─────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────
col_c1, col_c2 = st.columns(2)

with col_c1:
    mood_counts = mood_df["Mood"].value_counts().reset_index()
    mood_counts.columns = ["Mood","Count"]
    colors = {"Happy":"#22c55e","Neutral":"#f59e0b","Stressed":"#ef4444"}
    fig1 = px.pie(mood_counts, names="Mood", values="Count", hole=0.45,
                  title="Overall Mood Distribution",
                  color="Mood", color_discrete_map=colors)
    fig1.update_traces(hovertemplate="<b>%{label}</b><br>%{value} entries (%{percent})<extra></extra>")
    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=340)
    st.plotly_chart(fig1, use_container_width=True)

with col_c2:
    # Mood trend over time
    trend = mood_df.copy()
    trend["DateOnly"] = trend["Date"].dt.date
    trend["MoodNum"]  = trend["Mood"].map({"Happy":3,"Neutral":2,"Stressed":1})
    trend_agg = trend.groupby("DateOnly")["MoodNum"].mean().reset_index()
    trend_agg.columns = ["Date","Avg Mood"]

    fig2 = px.line(trend_agg, x="Date", y="Avg Mood", markers=True,
                   title="Mood Trend Over Time",
                   color_discrete_sequence=["#667eea"])
    fig2.update_yaxes(tickvals=[1,2,3], ticktext=["Stressed","Neutral","Happy"], range=[0.5,3.5])
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=340)
    st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────
# Mood History Table
# ─────────────────────────────────────────────
st.subheader("📋 Mood History")

mood_sorted = mood_df.sort_values("Date", ascending=False)
st.dataframe(
    mood_sorted[["Employee","Mood","Score","remarks","Date"]].rename(
        columns={"remarks":"Remarks"}
    ),
    height=350,
    use_container_width=True
)

# Alert if stressed employees
if role in ["Admin", "HR", "Manager"]:
    stressed = mood_df[mood_df["Mood"] == "Stressed"]["Employee"].value_counts()
    if not stressed.empty:
        st.divider()
        st.subheader("⚠️ Employees Needing Attention")
        st.caption("Employees with the most stressed mood entries")
        alert_df = stressed.reset_index()
        alert_df.columns = ["Employee","Stressed Entries"]
        st.dataframe(alert_df, use_container_width=True)