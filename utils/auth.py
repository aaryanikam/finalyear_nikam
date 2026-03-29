# utils/auth.py
"""
Authentication & Authorization — Workforce Intelligence System
Login interface: EXACTLY as original (plain Streamlit form, no custom CSS)
Backend: employee full name as username, firstname123 as password
"""

import streamlit as st
import hashlib
import datetime
from utils import database as db


# ─────────────────────────────────────────────
# Password Hashing
# ─────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────
# Login Logic
# ─────────────────────────────────────────────
def login(username: str, password: str):
    try:
        user = db.get_user_by_username(username.strip())
    except Exception as e:
        return False, f"Database error: {e}"

    if not user:
        return False, "User not found"

    if hash_password(password) != user["password"]:
        return False, "Invalid password"

    emp_id = db.get_emp_id_by_user_id(user["id"])

    st.session_state.clear()
    st.session_state["logged_in"] = True
    st.session_state["user"]      = user["username"]
    st.session_state["role"]      = user["role"]
    st.session_state["user_id"]   = user["id"]
    st.session_state["my_emp_id"] = emp_id

    return True, "Login successful"


# ─────────────────────────────────────────────
# Require Login (Guard) — ORIGINAL INTERFACE
# ─────────────────────────────────────────────
def require_login(roles_allowed=None):
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ Please login to continue")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit   = st.form_submit_button("Login")

        if submit:
            success, msg = login(username, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        st.stop()

    if roles_allowed:
        if st.session_state.get("role") not in roles_allowed:
            st.error("❌ Access denied for your role")
            st.stop()


# ─────────────────────────────────────────────
# Logout — ORIGINAL
# ─────────────────────────────────────────────
def logout_user():
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


# ─────────────────────────────────────────────
# Role Badge — ORIGINAL
# ─────────────────────────────────────────────
def show_role_badge():
    role = st.session_state.get("role")
    user = st.session_state.get("user")

    if user:
        st.sidebar.markdown(f"👤 **User:** `{user}`")
    if role:
        st.sidebar.markdown(f"🧑‍💼 **Role:** `{role}`")

    # CSV import for Admin / HR (added in sidebar, doesn't affect login UI)
    if role in ["Admin", "HR"]:
        st.sidebar.divider()
        st.sidebar.markdown("### 📥 Import Employees")
        with st.sidebar.expander("Upload CSV", expanded=False):
            _csv_import_widget()


def _csv_import_widget():
    import pandas as pd

    st.caption(
        "Required: Name, Department, Role, Status\n\n"
        "Optional: Age, Gender, Skills, Join_Date, Resign_Date, Salary, Location, sys_role"
    )

    sample = pd.DataFrame({
        "Name":        ["Aarti Sharma", "Rohan Verma"],
        "Age":         [28, 32],
        "Gender":      ["Female", "Male"],
        "Department":  ["HR", "IT"],
        "Role":        ["HR Manager", "Software Engineer"],
        "Skills":      ["Recruitment:5;Excel:4", "Python:4;SQL:3"],
        "Join_Date":   ["2022-06-01", "2021-03-15"],
        "Resign_Date": ["", ""],
        "Status":      ["Active", "Active"],
        "Salary":      [65000, 85000],
        "Location":    ["Mumbai", "Bangalore"],
        "sys_role":    ["HR", "Employee"],
    })
    st.download_button(
        "⬇️ Sample Template",
        sample.to_csv(index=False).encode("utf-8"),
        "employee_template.csv", "text/csv",
        use_container_width=True
    )

    uploaded = st.file_uploader("Choose CSV", type=["csv"], key="sidebar_csv_upload")
    if uploaded is not None:
        try:
            csv_df = pd.read_csv(uploaded)
            required = ["Name", "Department", "Role", "Status"]
            missing  = [c for c in required if c not in csv_df.columns]
            if missing:
                st.error(f"Missing columns: {missing}")
                return

            for col, default in [
                ("Age", 30), ("Gender", "Male"), ("Skills", "Excel:3"),
                ("Join_Date", datetime.date.today().strftime("%Y-%m-%d")),
                ("Resign_Date", ""), ("Salary", 50000),
                ("Location", "Unknown"), ("sys_role", "Employee")
            ]:
                if col not in csv_df.columns:
                    csv_df[col] = default
                csv_df[col] = csv_df[col].fillna(default)

            st.dataframe(csv_df.head(3), use_container_width=True)
            st.caption(f"{len(csv_df)} employees found")

            if st.button("✅ Import All", use_container_width=True, key="csv_confirm_import"):
                ok = err = 0
                for _, row in csv_df.iterrows():
                    try:
                        db.add_employee(row.to_dict())
                        ok += 1
                    except Exception:
                        err += 1
                db.sync_employee_users()
                st.success(f"✅ {ok} imported!" + (f" ⚠️ {err} skipped." if err else ""))
                st.rerun()
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")