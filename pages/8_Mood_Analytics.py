# pages/8_Mood_Analytics.py
"""
Employee Mood Analytics Dashboard — FIXED
- Fixed: mood_df uses mood_score column not 'mood'
- Fixed: date input crashes when df is empty
- Fixed: column name errors throughout
- PDF export with graphs working
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
import matplotlib.pyplot as plt

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -----------------------
# Auth
# -----------------------
st.set_page_config(page_title="Mood Analytics", page_icon="📊", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
st.title("📊 Mood Analytics Dashboard")

# -----------------------
# Load Data safely
# -----------------------
try:
    mood_df       = db.fetch_mood_logs()
    emp_df        = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    projects_df   = db.fetch_projects()
except Exception as e:
    st.error("Failed to load data.")
    st.exception(e)
    st.stop()

# Guard: no mood data at all
if mood_df.empty:
    st.info("📭 No mood survey data available yet. Ask employees to fill the Mood Tracker survey first.")
    st.stop()

# -----------------------
# Prepare data — use mood_score column (not 'mood')
# -----------------------
emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict() if not emp_df.empty else {}
mood_df = mood_df.copy()
mood_df["Employee"] = mood_df["emp_id"].map(emp_map).fillna("Unknown")
mood_df["DateTime"] = pd.to_datetime(mood_df["log_date"], errors="coerce")
mood_df["date"]     = mood_df["DateTime"].dt.date

# Derive mood label from mood_score
def score_to_label(score):
    try:
        s = int(score)
        if s >= 20:   return "😊 Happy"
        elif s >= 13: return "😐 Neutral"
        else:         return "😟 Stressed"
    except Exception:
        return "😐 Neutral"

mood_df["mood_label"] = mood_df["mood_score"].apply(score_to_label)

# mood_score_map for numeric trend
mood_score_map = {"😊 Happy": 3, "😐 Neutral": 2, "😟 Stressed": 1}
mood_df["MoodScore"] = mood_df["mood_label"].map(mood_score_map)

# Drop rows where date could not be parsed
mood_df = mood_df.dropna(subset=["date"])

# -----------------------
# Sidebar Filters — SAFE date defaults
# -----------------------
st.sidebar.header("🔍 Filters")

users = sorted(mood_df["Employee"].dropna().unique().tolist())
selected_user = st.sidebar.selectbox("Employee", ["All"] + users)

# Safe min/max dates
min_date = mood_df["date"].min() if not mood_df.empty else datetime.date.today() - datetime.timedelta(days=30)
max_date = mood_df["date"].max() if not mood_df.empty else datetime.date.today()

# Ensure they are real Python date objects (not NaT / pandas Timestamp)
try:
    min_date = min_date.date() if hasattr(min_date, "date") else min_date
except Exception:
    min_date = datetime.date.today() - datetime.timedelta(days=30)
try:
    max_date = max_date.date() if hasattr(max_date, "date") else max_date
except Exception:
    max_date = datetime.date.today()

# Clamp to valid range
if not isinstance(min_date, datetime.date):
    min_date = datetime.date.today() - datetime.timedelta(days=30)
if not isinstance(max_date, datetime.date):
    max_date = datetime.date.today()

start_date = st.sidebar.date_input("Start Date", value=min_date,
                                   min_value=datetime.date(2000, 1, 1),
                                   max_value=datetime.date.today())
end_date   = st.sidebar.date_input("End Date",   value=max_date,
                                   min_value=datetime.date(2000, 1, 1),
                                   max_value=datetime.date.today())

# -----------------------
# Filter
# -----------------------
filtered_df = mood_df.copy()
if selected_user != "All":
    filtered_df = filtered_df[filtered_df["Employee"] == selected_user]

filtered_df = filtered_df[
    (filtered_df["date"] >= start_date) &
    (filtered_df["date"] <= end_date)
]

if filtered_df.empty:
    st.warning("No mood data found for the selected filters. Try adjusting the date range.")
    st.stop()

# -----------------------
# KPI Row
# -----------------------
st.subheader("📌 Summary")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Logs",     len(filtered_df))
k2.metric("😊 Happy",       len(filtered_df[filtered_df["mood_label"] == "😊 Happy"]))
k3.metric("😐 Neutral",     len(filtered_df[filtered_df["mood_label"] == "😐 Neutral"]))
k4.metric("😟 Stressed",    len(filtered_df[filtered_df["mood_label"] == "😟 Stressed"]))

st.divider()

# -----------------------
# Trend Graph
# -----------------------
st.subheader("📈 Average Mood Over Time")

trend_df = (
    filtered_df.groupby("date")["MoodScore"]
    .mean()
    .reset_index()
    .rename(columns={"MoodScore": "avg_mood"})
)

if not trend_df.empty:
    trend_fig = px.line(
        trend_df, x="date", y="avg_mood", markers=True,
        title="Average Mood Score Over Time",
        labels={"avg_mood": "Avg Mood (1=Stressed, 3=Happy)", "date": "Date"},
        color_discrete_sequence=["#667eea"]
    )
    trend_fig.update_yaxes(tickmode="array", tickvals=[1, 2, 3],
                           ticktext=["😟 Stressed", "😐 Neutral", "😊 Happy"],
                           range=[0.5, 3.5])
    trend_fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        hoverlabel=dict(bgcolor="#667eea", font_color="white")
    )
    st.plotly_chart(trend_fig, use_container_width=True)
else:
    st.info("Not enough data for trend chart.")

# -----------------------
# Distribution Graph
# -----------------------
st.subheader("📊 Mood Distribution")

col_d1, col_d2 = st.columns(2)

with col_d1:
    dist_counts = filtered_df["mood_label"].value_counts().reset_index()
    dist_counts.columns = ["Mood", "Count"]

    mood_colors = {
        "😊 Happy":    "#22c55e",
        "😐 Neutral":  "#f59e0b",
        "😟 Stressed": "#ef4444"
    }
    dist_fig = px.bar(
        dist_counts, x="Mood", y="Count", text="Count",
        title="Mood Distribution",
        color="Mood",
        color_discrete_map=mood_colors
    )
    dist_fig.update_traces(textposition="outside")
    dist_fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=360
    )
    st.plotly_chart(dist_fig, use_container_width=True)

with col_d2:
    fig_pie = px.pie(
        dist_counts, names="Mood", values="Count",
        title="Mood Share",
        color="Mood",
        color_discrete_map=mood_colors,
        hole=0.4
    )
    fig_pie.update_traces(
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>"
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=360
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# -----------------------
# Comparison by Employee
# -----------------------
st.subheader("👥 Mood Comparison by Employee")

emp_avg = (
    filtered_df.groupby("Employee")["MoodScore"]
    .mean()
    .reset_index()
    .rename(columns={"MoodScore": "Avg_Mood"})
    .sort_values("Avg_Mood")
)

if not emp_avg.empty and len(emp_avg) > 1:
    compare_fig = px.bar(
        emp_avg, x="Avg_Mood", y="Employee",
        orientation="h",
        title="Average Mood Score per Employee",
        text=emp_avg["Avg_Mood"].round(2),
        color="Avg_Mood",
        color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
        range_color=[1, 3]
    )
    compare_fig.update_traces(textposition="outside")
    compare_fig.update_layout(
        xaxis=dict(range=[0, 3.5], tickvals=[1, 2, 3],
                   ticktext=["Stressed", "Neutral", "Happy"]),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=max(350, len(emp_avg) * 28),
        coloraxis_showscale=False
    )
    st.plotly_chart(compare_fig, use_container_width=True)
else:
    st.info("Select 'All' employees or a wider date range to see comparison.")

# -----------------------
# Stressed Employees Alert
# -----------------------
stressed = filtered_df[filtered_df["mood_label"] == "😟 Stressed"]["Employee"].value_counts()
if not stressed.empty:
    st.divider()
    st.subheader("⚠️ Frequently Stressed Employees")
    st.caption("Employees with the most stressed mood logs — consider HR check-in")

    alert_df = stressed.reset_index()
    alert_df.columns = ["Employee", "Stressed Log Count"]
    st.dataframe(alert_df, use_container_width=True)

# -----------------------
# Data Table
# -----------------------
st.divider()
st.subheader("📋 Mood Log Records")
display_cols = ["Employee", "mood_label", "mood_score", "remarks", "DateTime"]
display_cols = [c for c in display_cols if c in filtered_df.columns]
st.dataframe(
    filtered_df[display_cols].sort_values("DateTime", ascending=False).rename(
        columns={"mood_label": "Mood", "mood_score": "Score", "DateTime": "Date"}
    ),
    use_container_width=True,
    height=300
)

# -----------------------
# PDF EXPORT
# -----------------------
st.divider()
st.subheader("📄 Export PDF Report")

if role in ["Admin", "Manager", "HR"]:
    if st.button("🖨️ Generate PDF with Graphs"):
        pdf_buffer = io.BytesIO()
        try:
            # Graph 1: Trend
            fig1, ax1 = plt.subplots(figsize=(9, 4))
            ax1.plot(trend_df["date"], trend_df["avg_mood"], marker="o", color="#667eea")
            ax1.set_title("Average Mood Over Time")
            ax1.set_ylabel("Mood Score (1–3)")
            ax1.set_yticks([1, 2, 3])
            ax1.set_yticklabels(["Stressed", "Neutral", "Happy"])
            fig1.autofmt_xdate()
            plt.tight_layout()
            buf1 = io.BytesIO()
            fig1.savefig(buf1, format="png", dpi=150)
            plt.close(fig1)
            buf1.seek(0)

            # Graph 2: Distribution
            dc = filtered_df["mood_label"].value_counts()
            bar_colors = [mood_colors.get(m, "#667eea") for m in dc.index]
            fig2, ax2 = plt.subplots(figsize=(7, 4))
            bars = ax2.bar([m.split(" ", 1)[-1] for m in dc.index], dc.values, color=bar_colors)
            ax2.set_title("Mood Distribution")
            ax2.set_ylabel("Count")
            for bar in bars:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                         str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
            plt.tight_layout()
            buf2 = io.BytesIO()
            fig2.savefig(buf2, format="png", dpi=150)
            plt.close(fig2)
            buf2.seek(0)

            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=attendance_df,
                mood_df=filtered_df[["Employee", "mood_label", "mood_score", "remarks", "DateTime"]].rename(
                    columns={"mood_label": "Mood", "mood_score": "Score", "DateTime": "Date"}
                ),
                projects_df=projects_df,
                notifications_df=pd.DataFrame(),
                mood_fig=buf1.getvalue(),
                project_fig=buf2.getvalue()
            )
            pdf_buffer.seek(0)
            st.download_button(
                "⬇️ Download PDF",
                pdf_buffer,
                "mood_analytics_report.pdf",
                "application/pdf"
            )
            st.success("✅ PDF ready!")
        except Exception as e:
            st.error("PDF generation failed.")
            st.exception(e)
else:
    st.info("Only Admin / Manager / HR can download PDF.")