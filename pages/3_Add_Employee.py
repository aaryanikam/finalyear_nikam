# pages/3_Add_Employee.py
"""
Add Employee — Workforce Intelligence System
- Consistent sidebar
- Two-column clean layout
- Department dropdown from existing data
- Validation feedback
"""

import streamlit as st
import pandas as pd
import datetime
from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user

st.set_page_config(page_title="Add Employee", page_icon="➕", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "")
if role not in ["Admin", "HR"]:
    st.warning("⚠️ You do not have permission to add employees.")
    st.stop()

st.title("➕ Add New Employee")
st.caption("Fill in the details below. Fields marked * are required.")

# Load existing departments & roles for dropdown hints
try:
    emp_df = db.fetch_employees()
    existing_depts = sorted(emp_df["Department"].dropna().unique().tolist()) if not emp_df.empty else []
    existing_roles = sorted(emp_df["Role"].dropna().unique().tolist())       if not emp_df.empty else []
    existing_locs  = sorted(emp_df["Location"].dropna().unique().tolist())   if not emp_df.empty else []
except Exception:
    existing_depts, existing_roles, existing_locs = [], [], []

DEPT_OPTIONS = existing_depts if existing_depts else [
    "IT","HR","Finance","Sales","Marketing","Support","Operations","Legal"
]
LOC_OPTIONS = existing_locs if existing_locs else [
    "Bangalore","Mumbai","Delhi","Hyderabad","Chennai","Pune","Noida","Gurgaon"
]

with st.form("add_employee_form", clear_on_submit=True):
    st.subheader("👤 Personal Details")
    col1, col2, col3 = st.columns(3)
    emp_name   = col1.text_input("Full Name *")
    age        = col2.number_input("Age *", min_value=18, max_value=70, value=25)
    gender_val = col3.selectbox("Gender *", ["Male", "Female"])

    st.subheader("🏢 Job Details")
    col4, col5 = st.columns(2)

    # Department — select from existing or type custom
    dept_choice = col4.selectbox("Department *", ["-- Select --"] + DEPT_OPTIONS + ["Other (type below)"])
    dept_custom = col4.text_input("Custom Department (if Other)", placeholder="e.g. Data Science")
    department  = dept_custom.strip() if dept_choice in ["-- Select --", "Other (type below)"] and dept_custom.strip() else dept_choice

    role_input  = col5.text_input("Role / Designation *", placeholder="e.g. Software Engineer")

    col6, col7 = st.columns(2)
    salary     = col6.number_input("Salary (₹) *", min_value=0, value=50000, step=1000)
    location   = col7.selectbox("Location *", ["-- Select --"] + LOC_OPTIONS + ["Other"])
    loc_custom = col7.text_input("Custom Location (if Other)", placeholder="e.g. Jaipur")
    if location in ["-- Select --", "Other"] and loc_custom.strip():
        location = loc_custom.strip()

    st.subheader("📅 Employment Details")
    col8, col9 = st.columns(2)
    join_date  = col8.date_input("Join Date *", value=datetime.date.today())
    status     = col9.selectbox("Status *", ["Active", "Resigned"])

    resign_date = None
    if status == "Resigned":
        resign_date = col8.date_input("Resign Date *", value=datetime.date.today())

    st.subheader("🛠️ Skills")
    st.caption("Format: SkillName:Level (1–5), separated by semicolons. Example: Python:4;SQL:3;Excel:5")
    skills = st.text_input("Skills", placeholder="Python:4;SQL:3;Excel:5;Communication:4")

    st.divider()
    submit = st.form_submit_button("➕ Add Employee", use_container_width=True, type="primary")

    if submit:
        errors = []
        if not emp_name.strip():       errors.append("Name is required")
        if not role_input.strip():     errors.append("Role is required")
        if department == "-- Select --": errors.append("Department is required")
        if location   == "-- Select --": errors.append("Location is required")

        if errors:
            for err in errors:
                st.error(f"❌ {err}")
        else:
            new_row = {
                "Name":        emp_name.strip(),
                "Age":         int(age),
                "Gender":      gender_val,
                "Department":  department,
                "Role":        role_input.strip(),
                "Skills":      skills.strip() if skills.strip() else "Excel:3",
                "Join_Date":   str(join_date),
                "Resign_Date": str(resign_date) if status == "Resigned" and resign_date else "",
                "Status":      status,
                "Salary":      float(salary),
                "Location":    location,
            }
            try:
                db.add_employee(new_row)
                st.success(f"✅ Employee **{emp_name}** added successfully to {department}!")
            except Exception as e:
                st.error("❌ Failed to add employee.")
                st.exception(e)

# ── Recent additions preview
st.divider()
st.subheader("🕐 Recently Added Employees")
try:
    recent = db.fetch_employees()
    if not recent.empty:
        recent = recent.sort_values("Emp_ID", ascending=False).head(5)
        st.dataframe(
            recent[["Emp_ID","Name","Department","Role","Status","Join_Date"]],
            use_container_width=True
        )
except Exception:
    pass