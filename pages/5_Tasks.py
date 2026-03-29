# pages/5_Tasks.py
"""
Task Management — Workforce Intelligence System
- Consistent sidebar
- Plotly interactive analytics with hover
- Priority color coding
- Overdue task alerts
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

st.set_page_config(page_title="Task Management", page_icon="🗂️", layout="wide")
require_login()
show_role_badge()
logout_user()

role     = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

st.title("🗂️ Task Management")

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────
try:
    emp_df   = db.fetch_employees()
    emp_df   = emp_df[emp_df["Status"] == "Active"]
except Exception:
    emp_df = pd.DataFrame(columns=["Emp_ID","Name","Status"])

try:
    tasks_df = db.fetch_tasks()
except Exception:
    tasks_df = pd.DataFrame(columns=["task_id","task_name","emp_id","assigned_by","due_date","priority","status","remarks"])

emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict() if not emp_df.empty else {}

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────
if not tasks_df.empty:
    total_t     = len(tasks_df)
    pending_t   = len(tasks_df[tasks_df["status"] == "Pending"])
    inprog_t    = len(tasks_df[tasks_df["status"] == "In-Progress"])
    done_t      = len(tasks_df[tasks_df["status"] == "Completed"])

    try:
        tasks_df["due_date_dt"] = pd.to_datetime(tasks_df["due_date"], errors="coerce")
        overdue_t = len(tasks_df[
            (tasks_df["status"] != "Completed") &
            (tasks_df["due_date_dt"] < pd.Timestamp(datetime.date.today()))
        ])
    except Exception:
        overdue_t = 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📋 Total Tasks",    total_t)
    k2.metric("⏳ Pending",         pending_t)
    k3.metric("🔄 In Progress",     inprog_t)
    k4.metric("✅ Completed",        done_t)
    k5.metric("🚨 Overdue",          overdue_t)
    st.divider()

# ─────────────────────────────────────────────
# Assign Task (Admin / Manager)
# ─────────────────────────────────────────────
if role in ["Admin", "Manager"]:
    st.subheader("➕ Assign New Task")
    if not emp_df.empty:
        with st.form("assign_task", clear_on_submit=True):
            col1, col2 = st.columns(2)
            task_title = col1.text_input("Task Title *")
            assignee   = col2.selectbox(
                "Assign To *",
                (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist()
            )
            col3, col4, col5 = st.columns(3)
            due_date  = col3.date_input("Due Date", value=datetime.date.today() + datetime.timedelta(days=7))
            priority  = col4.selectbox("Priority", ["Low","Medium","High"])
            col5.write("")   # spacer
            remarks   = st.text_area("Remarks / Description", height=80)
            submit    = st.form_submit_button("🚀 Assign Task", use_container_width=True, type="primary")

            if submit:
                if not task_title.strip():
                    st.error("Task title is required.")
                else:
                    emp_id = int(assignee.split(" — ")[0])
                    try:
                        db.add_task({
                            "task_name":   task_title.strip(),
                            "emp_id":      emp_id,
                            "assigned_by": username,
                            "due_date":    due_date.strftime("%Y-%m-%d"),
                            "priority":    priority,
                            "status":      "Pending",
                            "remarks":     remarks or ""
                        })
                        tasks_df = db.fetch_tasks()
                        st.success(f"✅ Task **{task_title}** assigned successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error("❌ Failed to assign task.")
                        st.exception(e)
    else:
        st.info("No active employees found to assign tasks.")

st.divider()

# ─────────────────────────────────────────────
# Search / Filter Tasks
# ─────────────────────────────────────────────
st.subheader("🔎 Search & Filter Tasks")

col_s1, col_s2, col_s3 = st.columns(3)
search_text     = col_s1.text_input("Search (title / assignee / remarks)").lower().strip()
filter_status   = col_s2.selectbox("Status",   ["All","Pending","In-Progress","Completed"])
filter_priority = col_s3.selectbox("Priority", ["All","Low","Medium","High"])

tasks_display = tasks_df.copy() if not tasks_df.empty else pd.DataFrame()

if not tasks_display.empty:
    tasks_display["Employee"] = tasks_display["emp_id"].map(emp_map).fillna(
        tasks_display["emp_id"].astype(str)
    )

    # Mark overdue
    try:
        tasks_display["due_date_dt"] = pd.to_datetime(tasks_display["due_date"], errors="coerce")
        tasks_display["Overdue"] = (
            (tasks_display["status"] != "Completed") &
            (tasks_display["due_date_dt"] < pd.Timestamp(datetime.date.today()))
        )
    except Exception:
        tasks_display["Overdue"] = False

    if search_text:
        tasks_display = tasks_display[
            tasks_display["task_name"].str.lower().str.contains(search_text, na=False) |
            tasks_display["Employee"].str.lower().str.contains(search_text, na=False) |
            tasks_display["remarks"].str.lower().str.contains(search_text, na=False)
        ]
    if filter_status   != "All": tasks_display = tasks_display[tasks_display["status"]   == filter_status]
    if filter_priority != "All": tasks_display = tasks_display[tasks_display["priority"] == filter_priority]

    # Overdue alert
    overdue_rows = tasks_display[tasks_display["Overdue"] == True]
    if not overdue_rows.empty:
        st.warning(f"🚨 **{len(overdue_rows)} overdue tasks** in current view — review immediately!")

    show_cols = ["task_id","task_name","Employee","assigned_by","due_date","priority","status","remarks"]
    show_cols = [c for c in show_cols if c in tasks_display.columns]
    st.dataframe(tasks_display[show_cols], use_container_width=True, height=320)
    st.caption(f"{len(tasks_display)} tasks shown")
else:
    st.info("No tasks found.")
    st.dataframe(pd.DataFrame(columns=["task_id","task_name","Employee","due_date","priority","status"]))

# ─────────────────────────────────────────────
# Edit / Delete Task
# ─────────────────────────────────────────────
if role in ["Admin", "Manager"] and not tasks_display.empty:
    st.divider()
    st.subheader("✏️ Edit / Delete Task")

    task_options = tasks_display["task_id"].astype(str) + " — " + tasks_display["task_name"]
    sel_task_str = st.selectbox("Select Task", task_options.tolist())
    sel_id       = int(sel_task_str.split(" — ")[0])
    task_row     = tasks_display[tasks_display["task_id"] == sel_id].iloc[0].to_dict()

    with st.form("edit_task_form"):
        col_e1, col_e2 = st.columns(2)
        e_title    = col_e1.text_input("Task Title", value=task_row.get("task_name",""))
        e_assignee = col_e2.selectbox(
            "Assign To",
            (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist(),
            index=0
        )
        col_e3, col_e4, col_e5 = st.columns(3)
        try:
            e_due = col_e3.date_input("Due Date",
                                      value=pd.to_datetime(task_row.get("due_date", datetime.date.today())).date())
        except Exception:
            e_due = col_e3.date_input("Due Date", value=datetime.date.today())

        pri_list = ["Low","Medium","High"]
        e_priority = col_e4.selectbox("Priority", pri_list,
                                      index=pri_list.index(task_row.get("priority","Medium"))
                                      if task_row.get("priority") in pri_list else 1)

        stat_list = ["Pending","In-Progress","Completed"]
        e_status   = col_e5.selectbox("Status", stat_list,
                                      index=stat_list.index(task_row.get("status","Pending"))
                                      if task_row.get("status") in stat_list else 0)

        e_remarks  = st.text_area("Remarks", value=task_row.get("remarks",""))

        col_upd, col_del = st.columns(2)
        update_btn = col_upd.form_submit_button("💾 Save Changes",  use_container_width=True)
        delete_btn = col_del.form_submit_button("🗑️ Delete Task",   use_container_width=True)

        if update_btn:
            try:
                db.update_task(sel_id, {
                    "task_name": e_title.strip(),
                    "emp_id":    int(e_assignee.split(" — ")[0]),
                    "due_date":  e_due.strftime("%Y-%m-%d"),
                    "priority":  e_priority,
                    "status":    e_status,
                    "remarks":   e_remarks
                })
                st.success("✅ Task updated.")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to update task.")
                st.exception(e)

        if delete_btn:
            try:
                db.delete_task(sel_id)
                st.success("🗑️ Task deleted.")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to delete task.")
                st.exception(e)

# ─────────────────────────────────────────────
# Task Analytics — Plotly
# ─────────────────────────────────────────────
st.divider()
st.subheader("📊 Task Analytics")

if not tasks_df.empty:
    col_a1, col_a2, col_a3 = st.columns(3)

    with col_a1:
        sc = tasks_df["status"].value_counts().reset_index()
        sc.columns = ["Status","Count"]
        color_map  = {"Pending":"#f59e0b","In-Progress":"#667eea","Completed":"#22c55e"}
        fig1 = px.pie(sc, names="Status", values="Count", hole=0.45,
                      title="Tasks by Status", color="Status",
                      color_discrete_map=color_map)
        fig1.update_traces(hovertemplate="<b>%{label}</b><br>%{value} tasks (%{percent})<extra></extra>")
        fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=320)
        st.plotly_chart(fig1, use_container_width=True)

    with col_a2:
        pc = tasks_df["priority"].value_counts().reset_index()
        pc.columns = ["Priority","Count"]
        pcolor     = {"Low":"#22c55e","Medium":"#f59e0b","High":"#ef4444"}
        fig2 = px.bar(pc, x="Priority", y="Count", text="Count",
                      title="Tasks by Priority", color="Priority",
                      color_discrete_map=pcolor)
        fig2.update_traces(textposition="outside")
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           height=320, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col_a3:
        # Top 10 employees by task count
        if emp_map:
            tasks_df["Employee"] = tasks_df["emp_id"].map(emp_map).fillna("Unknown")
            top_emp = tasks_df["Employee"].value_counts().head(10).reset_index()
            top_emp.columns = ["Employee","Tasks"]
            fig3 = px.bar(top_emp, x="Tasks", y="Employee", orientation="h",
                          title="Top 10 Employees by Task Count",
                          text="Tasks", color="Tasks",
                          color_continuous_scale="Blues")
            fig3.update_traces(textposition="outside")
            fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               height=320, coloraxis_showscale=False,
                               yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No task data to display analytics.")