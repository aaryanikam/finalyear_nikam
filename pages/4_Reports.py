# pages/4_Reports.py
"""
Workforce Reports — Workforce Intelligence System
- Consistent sidebar (show_role_badge + logout_user)
- All charts converted to Plotly with hover
- Matplotlib versions kept only for PDF bytes
- Full master PDF with all 6 graphs embedded
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import io

from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user
from utils.pdf_export import generate_master_report
from utils.analytics import department_distribution, gender_ratio, average_salary_by_dept

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")

if role not in ["Admin", "Manager", "HR"]:
    st.warning("⚠️ Access denied. Admin / Manager / HR only.")
    st.stop()

st.title("📊 Workforce Reports")
st.caption("Comprehensive analytics across all workforce modules")

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────
def safe_fetch(func):
    try:
        return func()
    except Exception:
        return pd.DataFrame()

df_employees  = safe_fetch(db.fetch_employees)
df_mood       = safe_fetch(db.fetch_mood_logs)
df_attendance = safe_fetch(db.fetch_attendance)
df_projects   = safe_fetch(db.fetch_projects)
df_tasks      = safe_fetch(db.fetch_tasks)
df_feedback   = safe_fetch(db.fetch_feedback)

# ─────────────────────────────────────────────
# Sidebar Filters
# ─────────────────────────────────────────────
st.sidebar.header("🔍 Filters")

dept_opts = ["All"] + sorted(df_employees["Department"].dropna().unique().tolist()) \
            if not df_employees.empty else ["All"]

dept_filter   = st.sidebar.selectbox("Department", dept_opts)
status_filter = st.sidebar.selectbox("Status", ["All","Active","Resigned"])

filtered_df = df_employees.copy()
if dept_filter   != "All": filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
if status_filter != "All": filtered_df = filtered_df[filtered_df["Status"]     == status_filter]

# ─────────────────────────────────────────────
# Summary Metrics
# ─────────────────────────────────────────────
st.subheader("📌 Summary")

total_emp    = len(filtered_df)
active_emp   = int((filtered_df["Status"]  == "Active").sum())   if "Status"  in filtered_df.columns else 0
resigned_emp = int((filtered_df["Status"]  == "Resigned").sum()) if "Status"  in filtered_df.columns else 0
avg_salary   = int(filtered_df["Salary"].mean())                 if "Salary"  in filtered_df.columns and total_emp else 0
dept_count   = int(filtered_df["Department"].nunique())          if not filtered_df.empty else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("👥 Total Employees",  total_emp)
c2.metric("✅ Active",            active_emp)
c3.metric("🚪 Resigned",         resigned_emp)
c4.metric("💰 Avg Salary",       f"₹{avg_salary:,}")
c5.metric("🏢 Departments",      dept_count)

st.divider()

# ── PNG helpers (for PDF) ─────────────────────
def fig_to_png(fig_m):
    buf = io.BytesIO()
    fig_m.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    data = buf.read()
    plt.close(fig_m)
    return data

dept_png = gender_png = salary_png = mood_png = proj_png = att_png = None

# ─────────────────────────────────────────────
# SECTION 1 — Employee Distribution
# ─────────────────────────────────────────────
st.subheader("🏢 Employee Distribution")
col1, col2 = st.columns(2)

with col1:
    if not filtered_df.empty:
        dc = department_distribution(filtered_df, active_only=False).reset_index()
        dc.columns = ["Department","Count"]

        fig1 = px.bar(dc, x="Department", y="Count", text="Count",
                      title="Employees per Department",
                      color="Count", color_continuous_scale="Blues")
        fig1.update_traces(textposition="outside",
                           hovertemplate="<b>%{x}</b><br>%{y} employees<extra></extra>")
        fig1.update_layout(xaxis_tickangle=-30, plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", height=380, coloraxis_showscale=False)
        st.plotly_chart(fig1, use_container_width=True)

        fm, ax = plt.subplots(figsize=(7,4))
        b = ax.bar(dc["Department"], dc["Count"], color="#667eea")
        ax.set_title("Employees per Department"); ax.set_ylabel("Count")
        ax.tick_params(axis="x", rotation=30)
        for bar in b:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                    str(int(bar.get_height())), ha="center", va="bottom", fontsize=8)
        plt.tight_layout()
        dept_png = fig_to_png(fm)
    else:
        st.info("No department data.")

with col2:
    if not filtered_df.empty and "Gender" in filtered_df.columns:
        gc = gender_ratio(filtered_df, active_only=False).reset_index()
        gc.columns = ["Gender","Count"]

        fig2 = px.pie(gc, names="Gender", values="Count", hole=0.45,
                      title="Gender Distribution",
                      color="Gender",
                      color_discrete_map={"Male":"#667eea","Female":"#f472b6"})
        fig2.update_traces(hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>")
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=380)
        st.plotly_chart(fig2, use_container_width=True)

        fm2, ax2 = plt.subplots(figsize=(5,4))
        ax2.pie(gc["Count"], labels=gc["Gender"], autopct="%1.1f%%",
                colors=["#667eea","#f472b6"])
        ax2.set_title("Gender Distribution"); ax2.axis("equal")
        gender_png = fig_to_png(fm2)
    else:
        st.info("No gender data.")

st.divider()

# ─────────────────────────────────────────────
# SECTION 2 — Salary Analysis
# ─────────────────────────────────────────────
st.subheader("💰 Salary Analysis")
col3, col4 = st.columns(2)

with col3:
    if not filtered_df.empty and "Salary" in filtered_df.columns:
        avg_sal = average_salary_by_dept(filtered_df, active_only=False).reset_index()
        avg_sal.columns = ["Department","Avg Salary"]

        fig3 = px.bar(avg_sal, x="Department", y="Avg Salary", text="Avg Salary",
                      title="Average Salary by Department",
                      color="Avg Salary", color_continuous_scale="Greens")
        fig3.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside",
                           hovertemplate="<b>%{x}</b><br>Avg: ₹%{y:,.0f}<extra></extra>")
        fig3.update_layout(xaxis_tickangle=-30, plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", height=380, coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)

        fm3, ax3 = plt.subplots(figsize=(7,4))
        b3 = ax3.bar(avg_sal["Department"], avg_sal["Avg Salary"], color="#22c55e")
        ax3.set_title("Average Salary by Department"); ax3.set_ylabel("₹")
        ax3.tick_params(axis="x", rotation=30)
        for bar in b3:
            ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                     f"₹{int(bar.get_height()):,}", ha="center", va="bottom", fontsize=7)
        plt.tight_layout()
        salary_png = fig_to_png(fm3)
    else:
        st.info("No salary data.")

with col4:
    if not filtered_df.empty and "Salary" in filtered_df.columns:
        fig4 = px.box(filtered_df, x="Department", y="Salary",
                      title="Salary Range by Department",
                      color="Department", hover_data=["Name","Role"])
        fig4.update_layout(xaxis_tickangle=-30, plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", height=380, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# SECTION 3 — Mood Report
# ─────────────────────────────────────────────
st.subheader("😊 Mood Report")
col5, col6 = st.columns(2)

mood_colors = {"Happy":"#22c55e","Neutral":"#f59e0b","Stressed":"#ef4444"}

with col5:
    if not df_mood.empty:
        dm = df_mood.copy()
        dm["Mood"] = dm["mood_score"].apply(
            lambda x: "Happy" if x >= 20 else ("Neutral" if x >= 13 else "Stressed")
        )
        mc = dm["Mood"].value_counts().reset_index()
        mc.columns = ["Mood","Count"]

        fig5 = px.bar(mc, x="Mood", y="Count", text="Count",
                      title="Mood Distribution",
                      color="Mood", color_discrete_map=mood_colors)
        fig5.update_traces(textposition="outside",
                           hovertemplate="<b>%{x}</b><br>%{y} entries<extra></extra>")
        fig5.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           height=360, showlegend=False)
        st.plotly_chart(fig5, use_container_width=True)

        fm5, ax5 = plt.subplots(figsize=(6,4))
        bc5 = [mood_colors.get(m,"#667eea") for m in mc["Mood"]]
        b5 = ax5.bar(mc["Mood"], mc["Count"], color=bc5)
        ax5.set_title("Mood Distribution"); ax5.set_ylabel("Count")
        for bar in b5:
            ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                     str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
        plt.tight_layout()
        mood_png = fig_to_png(fm5)
    else:
        st.info("No mood data.")

with col6:
    if not df_mood.empty:
        fig6 = px.pie(mc, names="Mood", values="Count", hole=0.45,
                      title="Mood Share",
                      color="Mood", color_discrete_map=mood_colors)
        fig6.update_traces(hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>")
        fig6.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=360)
        st.plotly_chart(fig6, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# SECTION 4 — Project Report
# ─────────────────────────────────────────────
st.subheader("📈 Project Report")
col7, col8 = st.columns(2)

proj_colors = {"Active":"#667eea","Completed":"#22c55e","On Hold":"#f59e0b","Critical":"#ef4444"}

with col7:
    if not df_projects.empty:
        ps = df_projects["status"].value_counts().reset_index()
        ps.columns = ["Status","Count"]

        fig7 = px.bar(ps, x="Status", y="Count", text="Count",
                      title="Projects by Status",
                      color="Status", color_discrete_map=proj_colors)
        fig7.update_traces(textposition="outside",
                           hovertemplate="<b>%{x}</b><br>%{y} projects<extra></extra>")
        fig7.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           height=360, showlegend=False)
        st.plotly_chart(fig7, use_container_width=True)

        fm7, ax7 = plt.subplots(figsize=(6,4))
        bc7 = [proj_colors.get(s,"#667eea") for s in ps["Status"]]
        b7  = ax7.bar(ps["Status"], ps["Count"], color=bc7)
        ax7.set_title("Projects by Status"); ax7.set_ylabel("Count")
        for bar in b7:
            ax7.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                     str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
        plt.tight_layout()
        proj_png = fig_to_png(fm7)
    else:
        st.info("No project data.")

with col8:
    if not df_projects.empty and "progress" in df_projects.columns:
        prog = df_projects[["project_name","progress","status"]].sort_values("progress")
        fig8 = px.bar(prog, x="progress", y="project_name", orientation="h",
                      text="progress", title="Project Progress (%)",
                      color="status", color_discrete_map=proj_colors)
        fig8.update_traces(texttemplate="%{text}%", textposition="outside")
        fig8.update_layout(xaxis=dict(range=[0,115]),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           height=360)
        st.plotly_chart(fig8, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# SECTION 5 — Attendance Summary
# ─────────────────────────────────────────────
st.subheader("📋 Attendance Summary")
att_colors = {"Present":"#22c55e","Absent":"#ef4444","Half-day":"#f59e0b","Remote":"#667eea"}

if not df_attendance.empty:
    ac = df_attendance["status"].value_counts().reset_index()
    ac.columns = ["Status","Count"]

    col9, col10 = st.columns(2)
    with col9:
        fig9 = px.pie(ac, names="Status", values="Count", hole=0.45,
                      title="Attendance Breakdown",
                      color="Status", color_discrete_map=att_colors)
        fig9.update_traces(hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>")
        fig9.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=340)
        st.plotly_chart(fig9, use_container_width=True)

    with col10:
        fig10 = px.bar(ac, x="Status", y="Count", text="Count",
                       title="Attendance Status Count",
                       color="Status", color_discrete_map=att_colors)
        fig10.update_traces(textposition="outside")
        fig10.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            height=340, showlegend=False)
        st.plotly_chart(fig10, use_container_width=True)

    fm9, ax9 = plt.subplots(figsize=(6,4))
    bc9 = [att_colors.get(s,"#667eea") for s in ac["Status"]]
    b9  = ax9.bar(ac["Status"], ac["Count"], color=bc9)
    ax9.set_title("Attendance Breakdown"); ax9.set_ylabel("Count")
    for bar in b9:
        ax9.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                 str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    att_png = fig_to_png(fm9)
else:
    st.info("No attendance data.")

st.divider()

# ─────────────────────────────────────────────
# SECTION 6 — Tasks & Feedback Snapshot
# ─────────────────────────────────────────────
col11, col12 = st.columns(2)

with col11:
    st.subheader("🗂️ Tasks Overview")
    if not df_tasks.empty:
        tc = df_tasks["status"].value_counts().reset_index()
        tc.columns = ["Status","Count"]
        task_colors = {"Pending":"#f59e0b","In-Progress":"#667eea","Completed":"#22c55e"}
        fig11 = px.pie(tc, names="Status", values="Count", hole=0.45,
                       title="Tasks by Status",
                       color="Status", color_discrete_map=task_colors)
        fig11.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=320)
        st.plotly_chart(fig11, use_container_width=True)
    else:
        st.info("No task data.")

with col12:
    st.subheader("💬 Feedback Overview")
    if not df_feedback.empty:
        rc = df_feedback["rating"].value_counts().sort_index().reset_index()
        rc.columns = ["Rating","Count"]
        rc["Label"] = rc["Rating"].astype(str) + " ⭐"
        fig12 = px.bar(rc, x="Label", y="Count", text="Count",
                       title="Feedback Ratings",
                       color="Rating",
                       color_continuous_scale=["#ef4444","#f59e0b","#22c55e"],
                       range_color=[1,5])
        fig12.update_traces(textposition="outside")
        fig12.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            height=320, coloraxis_showscale=False, showlegend=False)
        st.plotly_chart(fig12, use_container_width=True)
    else:
        st.info("No feedback data.")

st.divider()

# ─────────────────────────────────────────────
# Export Master PDF
# ─────────────────────────────────────────────
st.subheader("📄 Download Master Workforce PDF")
st.caption("Generates a full PDF report with all charts and data tables")

if st.button("🖨️ Generate Master PDF", type="primary"):
    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=filtered_df,
            attendance_df=df_attendance,
            mood_df=df_mood,
            projects_df=df_projects,
            notifications_df=pd.DataFrame(),
            dept_fig=dept_png,
            gender_fig=gender_png,
            salary_fig=salary_png,
            mood_fig=mood_png,
            project_fig=proj_png,
            attendance_fig=att_png,
        )
        pdf_buffer.seek(0)
        st.download_button("⬇️ Download PDF", pdf_buffer,
                           "workforce_master_report.pdf", "application/pdf")
        st.success("✅ PDF ready!")
    except Exception as e:
        st.error("❌ Failed to generate PDF.")
        st.exception(e)