"""
Workforce Intelligence System — app.py
Employee login: username = full name, password = firstname123
sync_employee_users() creates login accounts for all employees on startup.
"""

import streamlit as st
import pandas as pd
import datetime
import random

st.set_page_config(
    page_title="Workforce Intelligence System",
    page_icon="🏢",
    layout="wide"
)

from utils import database as db
from utils.auth import require_login, logout_user, show_role_badge

# ─────────────────────────────────────────────
# Initialize DB + sync login accounts
# ─────────────────────────────────────────────
try:
    db.initialize_all_tables()
    db.create_default_admin()
    db.sync_employee_users()
except Exception as e:
    st.error("❌ Database initialization failed")
    st.exception(e)
    st.stop()

# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────
require_login()
role     = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
if st.session_state.get("logged_in"):
    with st.sidebar:
        st.title("🏢 Workforce System")
        show_role_badge()
        st.divider()
        logout_user()

# ─────────────────────────────────────────────
# Load Employees
# ─────────────────────────────────────────────
try:
    df = db.fetch_employees()
except Exception as e:
    df = pd.DataFrame()
    st.error("❌ Failed to load employees.")
    st.exception(e)

# ─────────────────────────────────────────────
# Auto-generate demo if DB is empty
# ─────────────────────────────────────────────
if df.empty:
    st.info("No employees found. Generating demo workforce (200 employees)...")

    def generate_employees(n=200):
        FIRST_M = ["Arjun","Rahul","Vikram","Amit","Rohan","Karan","Nikhil","Suresh",
                   "Deepak","Manoj","Sanjay","Rajesh","Aditya","Vivek","Harsh",
                   "Tushar","Gaurav","Yash","Ritesh","Dev","Ankit","Sahil","Mohit","Varun"]
        FIRST_F = ["Priya","Neha","Sneha","Anjali","Pooja","Kavya","Divya","Meera",
                   "Riya","Sonal","Tanvi","Shreya","Nidhi","Pallavi","Swati","Preeti",
                   "Ananya","Ishita","Kriti","Simran","Aarti","Bhavna","Rekha","Sunita","Geeta"]
        LAST    = ["Sharma","Verma","Singh","Gupta","Patel","Mehta","Joshi","Nair",
                   "Iyer","Rao","Reddy","Kumar","Malhotra","Kapoor","Saxena","Agarwal",
                   "Mishra","Pandey","Chauhan","Banerjee","Das","Bose","Shah","Desai","Pillai"]
        depts = {
            "IT":         ["Software Engineer","Senior Developer","DevOps Engineer","Tech Lead","IT Manager"],
            "HR":         ["HR Executive","HR Manager","Recruiter","L&D Specialist"],
            "Finance":    ["Accountant","Finance Analyst","Senior Accountant","Finance Manager"],
            "Sales":      ["Sales Executive","Sales Manager","Business Development","Key Account Manager"],
            "Marketing":  ["Marketing Executive","Content Writer","SEO Specialist","Marketing Manager"],
            "Support":    ["Support Executive","Support Lead","Customer Success Manager"],
            "Operations": ["Operations Executive","Operations Manager","Supply Chain Analyst"],
            "Legal":      ["Legal Counsel","Compliance Officer","Legal Executive"],
        }
        skills_map = {
            "IT":        ["Python","Java","JavaScript","SQL","React","AWS","Docker","Git"],
            "HR":        ["Communication","Recruitment","Excel","Onboarding","Training","Payroll"],
            "Finance":   ["Excel","Tally","SAP","Financial Modelling","Accounting","GST"],
            "Sales":     ["CRM","Negotiation","Communication","Lead Generation","Salesforce"],
            "Marketing": ["SEO","Google Ads","Content Writing","Canva","Social Media","Analytics"],
            "Support":   ["Communication","Zendesk","CRM","Problem Solving","Customer Service"],
            "Operations":["Excel","ERP","Logistics","SAP","Supply Chain","Project Management"],
            "Legal":     ["Contract Law","Compliance","Legal Research","Drafting","GDPR"],
        }
        locations  = ["Bangalore","Mumbai","Delhi","Hyderabad","Chennai","Pune","Noida","Gurgaon"]
        dept_keys  = list(depts.keys())
        weights    = [35,18,20,28,24,20,22,5]
        employees  = []
        random.seed(99)
        n = min(n, 500)

        for i in range(n):
            gender      = "Female" if i % 3 == 0 else "Male"
            fn          = random.choice(FIRST_F if gender == "Female" else FIRST_M)
            ln          = random.choice(LAST)
            dept        = random.choices(dept_keys, weights=weights)[0]
            pool        = skills_map[dept]
            chosen      = random.sample(pool, min(random.randint(3,4), len(pool)))
            skills      = ";".join(f"{s}:{random.randint(2,5)}" for s in chosen)
            base        = {"IT":70000,"HR":45000,"Finance":50000,"Sales":40000,
                           "Marketing":42000,"Support":35000,"Operations":45000,"Legal":60000}[dept]
            role_choice = random.choice(depts[dept])
            salary      = random.randint(base+30000, base+80000) \
                          if any(x in role_choice for x in ["Manager","Lead","Head"]) \
                          else random.randint(base-5000, base+20000)
            days_ago    = random.randint(30, 1800)
            join_date   = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
            status      = "Resigned" if random.random() < 0.15 else "Active"
            res_days    = random.randint(10, max(11, days_ago-10))
            resign      = (datetime.datetime.now() - datetime.timedelta(days=res_days)).strftime("%Y-%m-%d") \
                          if status == "Resigned" else ""

            if "Manager" in role_choice or "Head" in role_choice:
                sys_role = "Manager"
            elif dept == "HR" and "Manager" in role_choice:
                sys_role = "HR"
            else:
                sys_role = "Employee"

            employees.append({
                "Name":        f"{fn} {ln}",
                "Age":         random.randint(22,55),
                "Gender":      gender,
                "Department":  dept,
                "Role":        role_choice,
                "Skills":      skills,
                "Join_Date":   join_date,
                "Resign_Date": resign,
                "Status":      status,
                "Salary":      float(salary),
                "Location":    random.choice(locations),
                "sys_role":    sys_role,
            })

        return pd.DataFrame(employees)

    gen_df = generate_employees(200)
    for _, row in gen_df.iterrows():
        db.add_employee(row.to_dict())
    db.sync_employee_users()
    st.success(f"✅ {len(gen_df)} employees created with login accounts.")
    st.rerun()

# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────
st.title("📊 Workforce Intelligence Dashboard")
st.caption("Central overview of workforce data")

total_emp    = len(df)
active_emp   = int((df["Status"] == "Active").sum())
resigned_emp = int((df["Status"] == "Resigned").sum())
dept_count   = int(df["Department"].nunique())
avg_sal      = int(df["Salary"].mean()) if "Salary" in df.columns and total_emp else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("👥 Total Employees",  total_emp)
c2.metric("✅ Active",           active_emp)
c3.metric("🚪 Resigned",         resigned_emp)
c4.metric("🏢 Departments",      dept_count)
c5.metric("💰 Avg Salary",       f"₹{avg_sal:,}")

st.divider()

st.subheader("👩‍💼 Recent Employees")
st.dataframe(
    df[["Emp_ID","Name","Department","Role","Status","Join_Date"]]
    .sort_values("Join_Date", ascending=False).head(10),
    use_container_width=True
)

st.info(
    "📂 Use the **left sidebar** to navigate — Employees, Tasks, Attendance, "
    "Mood Tracker, Analytics, Feedback, Skills, Projects, Notifications, "
    "Email Center, AI Assistant, AI Summary."
)