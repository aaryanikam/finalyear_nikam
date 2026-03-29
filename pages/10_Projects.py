# pages/10_Projects.py
"""
Project Health Tracker — Workforce Intelligence System
- Consistent sidebar (show_role_badge + logout_user)
- Plotly interactive charts with hover
- Health scoring engine (Progress + Mood + Attendance + Deadline)
- Gantt timeline view
- Add/Edit/Delete project forms
- PDF export with graph
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import datetime
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

st.set_page_config(page_title="Project Health", page_icon="📈", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
st.title("📈 Project Health Tracker")

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────
try:
    project_df    = db.fetch_projects()
    emp_df        = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    mood_df       = db.fetch_mood_logs()
except Exception as e:
    st.error("Failed to load data.")
    st.exception(e)
    st.stop()

emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict() if not emp_df.empty else {}

# ─────────────────────────────────────────────
# Health Scoring Helpers
# ─────────────────────────────────────────────
def attendance_score(emp_id):
    if attendance_df.empty: return 0
    ea = attendance_df[attendance_df["emp_id"] == emp_id]
    if ea.empty: return 0
    ratio = len(ea[ea["status"].isin(["Present","Remote"])]) / len(ea)
    return 20 if ratio > 0.8 else (10 if ratio >= 0.5 else 0)

def mood_score_fn(emp_id):
    if mood_df.empty: return 0
    em = mood_df[mood_df["emp_id"] == emp_id]
    if em.empty: return 0
    last = em.sort_values("log_date").iloc[-1]
    try:
        score = int(last["mood_score"])
        return 20 if score >= 20 else (10 if score >= 13 else 0)
    except Exception:
        return 0

def deadline_penalty(due_date_str):
    try:
        due = pd.to_datetime(due_date_str)
        days_left = (due - pd.Timestamp.today()).days
        if days_left < 0:   return -20
        elif days_left < 7: return -10
        return 0
    except Exception:
        return 0

# ─────────────────────────────────────────────
# Build Health DataFrame
# ─────────────────────────────────────────────
if not project_df.empty:
    project_df["Owner"] = project_df["owner_emp_id"].map(emp_map).fillna("Unknown")
    health_rows = []
    for _, row in project_df.iterrows():
        progress   = int(row.get("progress", 0))
        owner_id   = row.get("owner_emp_id")
        m_score    = mood_score_fn(owner_id)
        a_score    = attendance_score(owner_id)
        d_penalty  = deadline_penalty(row.get("due_date",""))
        health     = min(100, max(0, progress + m_score + a_score + d_penalty))

        if health >= 70:    h_status = "🟢 Healthy"
        elif health >= 40:  h_status = "🟡 At Risk"
        else:               h_status = "🔴 Critical"

        try:
            days_left = (pd.to_datetime(row["due_date"]) - pd.Timestamp.today()).days
        except Exception:
            days_left = 0

        health_rows.append({
            "project_id":   row["project_id"],
            "Project":      row["project_name"],
            "Owner":        row["Owner"],
            "Status":       row["status"],
            "Progress (%)": progress,
            "Health Score": health,
            "Health Status":h_status,
            "Start Date":   row.get("start_date",""),
            "Due Date":     row.get("due_date",""),
            "Days Left":    days_left,
        })

    health_df = pd.DataFrame(health_rows)
else:
    health_df = pd.DataFrame()

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────
if not health_df.empty:
    total_p    = len(health_df)
    healthy    = len(health_df[health_df["Health Status"] == "🟢 Healthy"])
    at_risk    = len(health_df[health_df["Health Status"] == "🟡 At Risk"])
    critical   = len(health_df[health_df["Health Status"] == "🔴 Critical"])
    completed  = len(health_df[health_df["Status"] == "Completed"])
    overdue    = len(health_df[health_df["Days Left"] < 0])

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("📋 Total Projects", total_p)
    k2.metric("🟢 Healthy",        healthy)
    k3.metric("🟡 At Risk",        at_risk)
    k4.metric("🔴 Critical",       critical)
    k5.metric("✅ Completed",       completed)
    k6.metric("⏰ Overdue",         overdue)
    st.divider()

# ─────────────────────────────────────────────
# Add Project (Admin / Manager)
# ─────────────────────────────────────────────
if role in ["Admin","Manager"]:
    with st.expander("➕ Add New Project", expanded=False):
        with st.form("add_project_form"):
            col1, col2 = st.columns(2)
            p_name   = col1.text_input("Project Name *")
            p_owner  = col2.selectbox("Project Owner",
                                      (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist()
                                      if not emp_df.empty else [])
            col3, col4, col5 = st.columns(3)
            p_status = col3.selectbox("Status", ["Active","On Hold","Completed","Critical"])
            p_prog   = col4.slider("Progress (%)", 0, 100, 0)
            col6, col7 = st.columns(2)
            p_start  = col6.date_input("Start Date", datetime.date.today())
            p_due    = col7.date_input("Due Date",   datetime.date.today() + datetime.timedelta(days=30))

            add_btn = st.form_submit_button("➕ Add Project", use_container_width=True, type="primary")
            if add_btn:
                if not p_name.strip():
                    st.error("Project name is required.")
                else:
                    try:
                        owner_id = int(p_owner.split(" — ")[0]) if p_owner else None
                        db.add_project({
                            "project_name":  p_name.strip(),
                            "owner_emp_id":  owner_id,
                            "status":        p_status,
                            "progress":      p_prog,
                            "start_date":    str(p_start),
                            "due_date":      str(p_due),
                        })
                        st.success(f"✅ Project '{p_name}' added.")
                        st.rerun()
                    except Exception as e:
                        st.error("❌ Failed to add project."); st.exception(e)

# ─────────────────────────────────────────────
# Project Overview Table
# ─────────────────────────────────────────────
st.subheader("📋 Project Health Overview")

if not health_df.empty:
    # Filter
    col_f1, col_f2 = st.columns(2)
    f_status = col_f1.selectbox("Filter by Status",        ["All","Active","Completed","On Hold","Critical"])
    f_health = col_f2.selectbox("Filter by Health",        ["All","🟢 Healthy","🟡 At Risk","🔴 Critical"])

    show_df = health_df.copy()
    if f_status != "All": show_df = show_df[show_df["Status"]        == f_status]
    if f_health != "All": show_df = show_df[show_df["Health Status"] == f_health]

    st.dataframe(show_df.drop(columns=["project_id"], errors="ignore"),
                 use_container_width=True, height=340)
else:
    st.info("No project data. Add projects above.")

# ─────────────────────────────────────────────
# Edit / Delete (Admin / Manager)
# ─────────────────────────────────────────────
if role in ["Admin","Manager"] and not health_df.empty:
    with st.expander("✏️ Edit / Delete Project", expanded=False):
        proj_opts = health_df["project_id"].astype(str) + " — " + health_df["Project"]
        sel_str   = st.selectbox("Select Project", proj_opts.tolist())
        sel_pid   = int(sel_str.split(" — ")[0])
        sel_row   = project_df[project_df["project_id"] == sel_pid].iloc[0]

        with st.form("edit_project_form"):
            col_e1, col_e2 = st.columns(2)
            e_name   = col_e1.text_input("Project Name", value=sel_row["project_name"])
            owner_opts = (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist() if not emp_df.empty else []
            e_owner  = col_e2.selectbox("Owner", owner_opts, index=0)
            col_e3, col_e4 = st.columns(2)
            stat_list = ["Active","On Hold","Completed","Critical"]
            e_status = col_e3.selectbox("Status", stat_list,
                                        index=stat_list.index(sel_row["status"])
                                        if sel_row["status"] in stat_list else 0)
            e_prog   = col_e4.slider("Progress (%)", 0, 100, int(sel_row["progress"]))
            col_e5, col_e6 = st.columns(2)
            try:
                e_start = col_e5.date_input("Start Date", value=pd.to_datetime(sel_row["start_date"]).date())
                e_due   = col_e6.date_input("Due Date",   value=pd.to_datetime(sel_row["due_date"]).date())
            except Exception:
                e_start = col_e5.date_input("Start Date", value=datetime.date.today())
                e_due   = col_e6.date_input("Due Date",   value=datetime.date.today())

            col_u, col_d = st.columns(2)
            upd_btn = col_u.form_submit_button("💾 Save Changes", use_container_width=True)
            del_btn = col_d.form_submit_button("🗑️ Delete Project", use_container_width=True)

            if upd_btn:
                try:
                    db.update_project(sel_pid, {
                        "project_name": e_name.strip(),
                        "owner_emp_id": int(e_owner.split(" — ")[0]) if e_owner else None,
                        "status":       e_status,
                        "progress":     e_prog,
                        "start_date":   str(e_start),
                        "due_date":     str(e_due),
                    })
                    st.success("✅ Project updated."); st.rerun()
                except Exception as e:
                    st.error("❌ Failed."); st.exception(e)

            if del_btn:
                try:
                    db.delete_project(sel_pid)
                    st.success("🗑️ Project deleted."); st.rerun()
                except Exception as e:
                    st.error("❌ Failed."); st.exception(e)

st.divider()

# ─────────────────────────────────────────────
# Analytics Charts — Plotly
# ─────────────────────────────────────────────
st.subheader("📊 Project Analytics")
project_png = None

if not health_df.empty:
    col_a1, col_a2 = st.columns(2)

    h_colors = {"🟢 Healthy":"#22c55e","🟡 At Risk":"#f59e0b","🔴 Critical":"#ef4444"}

    with col_a1:
        hc = health_df["Health Status"].value_counts().reset_index()
        hc.columns = ["Health","Count"]
        fig_h = px.pie(hc, names="Health", values="Count", hole=0.45,
                       title="Health Status Distribution",
                       color="Health", color_discrete_map=h_colors)
        fig_h.update_traces(hovertemplate="<b>%{label}</b><br>%{value} projects (%{percent})<extra></extra>")
        fig_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=340)
        st.plotly_chart(fig_h, use_container_width=True)

    with col_a2:
        fig_prog = px.bar(
            health_df.sort_values("Progress (%)"),
            x="Progress (%)", y="Project", orientation="h",
            text="Progress (%)",
            title="Progress per Project",
            color="Health Status",
            color_discrete_map=h_colors
        )
        fig_prog.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_prog.update_layout(
            xaxis=dict(range=[0,115]),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=340, showlegend=True
        )
        st.plotly_chart(fig_prog, use_container_width=True)

    # Health Score vs Progress scatter
    st.subheader("🎯 Health Score vs Progress")
    fig_scatter = px.scatter(
        health_df,
        x="Progress (%)", y="Health Score",
        color="Health Status", color_discrete_map=h_colors,
        size="Health Score", hover_data=["Project","Owner","Status","Days Left"],
        title="Health Score vs Progress (bubble size = Health Score)"
    )
    fig_scatter.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Gantt Timeline
    st.subheader("📅 Project Timeline (Gantt)")
    gantt_df = health_df.copy()
    gantt_df["Start Date"] = pd.to_datetime(gantt_df["Start Date"], errors="coerce")
    gantt_df["Due Date"]   = pd.to_datetime(gantt_df["Due Date"],   errors="coerce")
    gantt_df = gantt_df.dropna(subset=["Start Date","Due Date"])

    if not gantt_df.empty:
        fig_gantt = px.timeline(
            gantt_df,
            x_start="Start Date", x_end="Due Date",
            y="Project", color="Health Status",
            color_discrete_map=h_colors,
            hover_data=["Owner","Status","Progress (%)","Days Left"],
            title="Project Timelines"
        )
        fig_gantt.update_yaxes(autorange="reversed")
        fig_gantt.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=max(360, len(gantt_df)*38)
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

    # Matplotlib PNG for PDF
    hc_data = health_df["Health Status"].value_counts()
    bar_colors = [{"🟢 Healthy":"#22c55e","🟡 At Risk":"#f59e0b","🔴 Critical":"#ef4444"}.get(k,"#667eea")
                  for k in hc_data.index]
    fm, ax = plt.subplots(figsize=(7,4))
    b = ax.bar([h.split(" ",1)[-1] for h in hc_data.index], hc_data.values, color=bar_colors)
    ax.set_title("Project Health Distribution"); ax.set_ylabel("Count")
    for bar in b:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    buf = io.BytesIO(); fm.savefig(buf, format="png", dpi=150); buf.seek(0)
    project_png = buf.read(); plt.close(fm)

else:
    st.info("No project data for analytics.")

# ─────────────────────────────────────────────
# PDF Export
# ─────────────────────────────────────────────
st.divider()
st.subheader("📄 Download Project Report PDF")

if st.button("🖨️ Generate PDF", type="primary"):
    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=emp_df,
            attendance_df=attendance_df,
            mood_df=mood_df,
            projects_df=health_df if not health_df.empty else project_df,
            notifications_df=pd.DataFrame(),
            project_fig=project_png
        )
        pdf_buffer.seek(0)
        st.download_button("⬇️ Download PDF", pdf_buffer,
                           "project_health_report.pdf", "application/pdf")
        st.success("✅ PDF ready!")
    except Exception as e:
        st.error("❌ Failed to generate PDF."); st.exception(e)