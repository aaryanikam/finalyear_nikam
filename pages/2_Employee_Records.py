# pages/2_Employee_Records.py
"""
Employee Records — Workforce Intelligence System
- Consistent sidebar
- Role Management: Admin/HR can assign sys_role to any employee
- sys_role change instantly updates their login role
- Plotly interactive charts, CSV export
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user

st.set_page_config(page_title="Employee Records", page_icon="📄", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "")
if role not in ["Admin", "HR", "Manager"]:
    st.warning("⚠️ You do not have permission to view this page.")
    st.stop()

st.title("📄 Employee Records")

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────
try:
    df = db.fetch_employees()
except Exception as e:
    st.error("Failed to fetch employee data.")
    st.exception(e)
    df = pd.DataFrame()

if df.empty:
    st.info("No employee records available.")
    st.stop()

df = df.sort_values("Emp_ID").reset_index(drop=True)
df.insert(0, "SR_No", range(1, len(df)+1))

# ─────────────────────────────────────────────
# Quick Stats
# ─────────────────────────────────────────────
k1,k2,k3,k4 = st.columns(4)
k1.metric("👥 Total",       len(df))
k2.metric("✅ Active",      len(df[df["Status"] == "Active"]))
k3.metric("🚪 Resigned",    len(df[df["Status"] == "Resigned"]))
k4.metric("🏢 Departments", df["Department"].nunique())
st.divider()

# ─────────────────────────────────────────────
# Sidebar Filters
# ─────────────────────────────────────────────
st.sidebar.header("🔍 Filters")
f_dept   = st.sidebar.selectbox("Department", ["All"] + sorted(df["Department"].dropna().unique()))
f_status = st.sidebar.selectbox("Status",     ["All","Active","Resigned"])
f_role   = st.sidebar.selectbox("System Role",["All","Admin","HR","Manager","Employee"])

# ─────────────────────────────────────────────
# Search & Filter
# ─────────────────────────────────────────────
st.subheader("🔍 Search Employees")
search = st.text_input("Search by Name / Department / Role / Location").strip().lower()

filt = df.copy()
if f_dept   != "All": filt = filt[filt["Department"] == f_dept]
if f_status != "All": filt = filt[filt["Status"]     == f_status]
if f_role   != "All" and "sys_role" in filt.columns:
    filt = filt[filt["sys_role"] == f_role]
if search:
    filt = filt[
        filt["Name"].str.lower().str.contains(search, na=False) |
        filt["Department"].str.lower().str.contains(search, na=False) |
        filt["Role"].str.lower().str.contains(search, na=False) |
        filt["Location"].str.lower().str.contains(search, na=False)
    ]

st.caption(f"Showing {len(filt)} of {len(df)} employees")

display_cols = ["SR_No","Emp_ID","Name","Age","Gender","Department",
                "Role","Status","Salary","Location","Join_Date"]
if "sys_role" in filt.columns:
    display_cols.append("sys_role")

st.dataframe(filt[display_cols].rename(columns={"sys_role":"System Role"}),
             use_container_width=True, height=380)

csv_data = filt.drop(columns=["SR_No"], errors="ignore").to_csv(index=False).encode("utf-8")
st.download_button("📥 Export as CSV", csv_data, "employees.csv", "text/csv")

st.divider()

# ─────────────────────────────────────────────
# Quick Charts
# ─────────────────────────────────────────────
st.subheader("📊 Quick Analytics")
col1, col2 = st.columns(2)

with col1:
    dc = filt["Department"].value_counts().reset_index()
    dc.columns = ["Department","Count"]
    fig = px.bar(dc, x="Department", y="Count", text="Count",
                 title="Employees by Department",
                 color="Count", color_continuous_scale="Blues")
    fig.update_traces(textposition="outside")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      height=320, coloraxis_showscale=False, xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    if "Salary" in filt.columns:
        fig2 = px.box(filt, x="Department", y="Salary",
                      title="Salary Range by Department",
                      color="Department", hover_data=["Name","Role"])
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           height=320, showlegend=False, xaxis_tickangle=-30)
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# ROLE MANAGEMENT (Admin / HR only)
# ─────────────────────────────────────────────
if role in ["Admin", "HR"]:
    st.subheader("🔐 Role Management")
    st.caption(
        "Assign a **System Role** to any employee. "
        "This controls what pages they can access when they log in.\n\n"
        "Their login password stays the same — only their access level changes."
    )

    # Role legend
    col_l1, col_l2, col_l3, col_l4 = st.columns(4)
    col_l1.markdown("🔴 **Admin** — Full access to everything")
    col_l2.markdown("🟣 **HR** — Employees, Mood, Feedback, Notifications")
    col_l3.markdown("🟡 **Manager** — Tasks, Projects, Reports, Teams")
    col_l4.markdown("🟢 **Employee** — Own tasks, mood survey, notifications")

    st.markdown("")

    active_emp = df[df["Status"] == "Active"].copy() if "Status" in df.columns else df.copy()

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        emp_opts = (
            active_emp["Emp_ID"].astype(str) + " — " +
            active_emp["Name"] + " (" +
            (active_emp["sys_role"] if "sys_role" in active_emp.columns else "Employee") + ")"
        ).tolist()

        selected = st.selectbox("Select Employee", emp_opts, key="role_mgmt_select")
        sel_id   = int(selected.split(" — ")[0])
        sel_row  = df[df["Emp_ID"] == sel_id].iloc[0]

        current_sys_role = str(sel_row.get("sys_role", "Employee")) \
                           if "sys_role" in sel_row.index else "Employee"

    with col_r2:
        sys_role_opts = ["Employee","Manager","HR","Admin"]
        new_sys_role  = st.selectbox(
            "Assign System Role",
            sys_role_opts,
            index=sys_role_opts.index(current_sys_role)
            if current_sys_role in sys_role_opts else 0,
            key="new_sys_role"
        )

        emp_name     = sel_row["Name"]
        first_name   = emp_name.strip().split()[0].lower()
        login_name   = emp_name
        login_pass   = f"{first_name}123"

        st.info(
            f"**Login credentials for {emp_name}:**\n\n"
            f"👤 Username: `{login_name}`\n\n"
            f"🔑 Password: `{login_pass}`\n\n"
            f"Current role: `{current_sys_role}` → New role: `{new_sys_role}`"
        )

    if st.button("💾 Update System Role", type="primary"):
        if new_sys_role == current_sys_role:
            st.info("No change — role is already the same.")
        else:
            try:
                db.update_employee_sys_role(sel_id, new_sys_role)
                st.success(
                    f"✅ **{emp_name}** → role updated to **{new_sys_role}**. "
                    f"They can login with `{login_name}` / `{login_pass}`."
                )
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to update role.")
                st.exception(e)

    st.divider()

    # Bulk Role Assignment Table
    st.subheader("📋 Current System Roles")
    if "sys_role" in df.columns:
        role_summary = df[df["Status"] == "Active"].groupby("sys_role")["Name"].count().reset_index()
        role_summary.columns = ["System Role","Employee Count"]
        st.dataframe(role_summary, use_container_width=True)

        role_detail = df[["Emp_ID","Name","Department","Role","sys_role"]].rename(
            columns={"sys_role":"System Role"}
        )
        st.dataframe(role_detail, use_container_width=True, height=300)

st.divider()

# ─────────────────────────────────────────────
# Edit Employee Details (Admin / HR only)
# ─────────────────────────────────────────────
if role in ["Admin", "HR"]:
    st.subheader("✏️ Edit / Delete Employee")

    if filt.empty:
        st.info("No employees match current filter.")
    else:
        emp_options = filt["Emp_ID"].astype(str) + " — " + filt["Name"] + " (" + filt["Department"] + ")"
        selected    = st.selectbox("Select Employee to Edit", emp_options.tolist(), key="edit_emp_select")
        emp_id      = int(selected.split(" — ")[0])
        emp_row     = df[df["Emp_ID"] == emp_id].iloc[0]

        with st.form("edit_employee_form"):
            col_a, col_b = st.columns(2)
            name       = col_a.text_input("Name",       emp_row["Name"])
            age        = col_b.number_input("Age",       value=int(emp_row["Age"]), min_value=18, max_value=70)
            gender     = col_a.selectbox("Gender",       ["Male","Female"],
                                         index=0 if emp_row["Gender"]=="Male" else 1)
            dept       = col_b.text_input("Department",  emp_row["Department"])
            role_input = col_a.text_input("Role",        emp_row["Role"])
            skills     = col_b.text_input("Skills",      emp_row["Skills"])
            status     = col_a.selectbox("Status",       ["Active","Resigned"],
                                         index=0 if emp_row["Status"]=="Active" else 1)
            salary     = col_b.number_input("Salary",    value=int(emp_row["Salary"]), min_value=0)
            location   = col_a.text_input("Location",    emp_row["Location"])

            col_u, col_d = st.columns(2)
            update_btn = col_u.form_submit_button("💾 Update", use_container_width=True)
            delete_btn = col_d.form_submit_button("🗑️ Delete", use_container_width=True)

            if update_btn:
                try:
                    db.update_employee(emp_id, {
                        "Name": name, "Age": age, "Gender": gender,
                        "Department": dept, "Role": role_input,
                        "Skills": skills, "Status": status,
                        "Salary": salary, "Location": location
                    })
                    st.success("✅ Employee updated.")
                    st.rerun()
                except Exception as e:
                    st.error("❌ Failed."); st.exception(e)

            if delete_btn:
                try:
                    db.delete_employee(emp_id)
                    st.success("🗑️ Employee deleted.")
                    st.rerun()
                except Exception as e:
                    st.error("❌ Failed."); st.exception(e)
else:
    st.info("ℹ️ Only Admin and HR can edit or delete employees.")