# utils/analytics.py
"""
Analytics Utilities — Workforce Intelligence System
Handles summaries, trends, and options for employees, feedback, mood, tasks, and skills.
"""

import pandas as pd
from datetime import datetime

# --------------------------
# EMPLOYEE SUMMARY
# --------------------------
def get_summary(df: pd.DataFrame):
    """
    Return a dict with total employees, active, and resigned counts.
    """
    if df is None or df.empty:
        return {"total": 0, "active": 0, "resigned": 0}
    
    total = len(df)
    active = int(len(df[df.get("Status", "") == "Active"])) if "Status" in df.columns else 0
    resigned = int(len(df[df.get("Status", "") == "Resigned"])) if "Status" in df.columns else 0
    return {"total": total, "active": active, "resigned": resigned}


# --------------------------
# DEPARTMENT DISTRIBUTION
# --------------------------
def department_distribution(df: pd.DataFrame, active_only=True) -> pd.Series:
    """
    Return count of employees per department.
    Optionally filter only active employees.
    """
    if df is None or df.empty or "Department" not in df.columns:
        return pd.Series(dtype=int)
    if active_only and "Status" in df.columns:
        df = df[df["Status"] == "Active"]
    return df["Department"].value_counts().sort_index()


# --------------------------
# GENDER RATIO
# --------------------------
def gender_ratio(df: pd.DataFrame, active_only=True) -> pd.Series:
    """
    Return count of Male/Female employees.
    """
    if df is None or df.empty or "Gender" not in df.columns:
        return pd.Series(dtype=int)
    if active_only and "Status" in df.columns:
        df = df[df["Status"] == "Active"]
    return df["Gender"].value_counts().reindex(["Male", "Female"], fill_value=0)


# --------------------------
# AVERAGE SALARY BY DEPARTMENT
# --------------------------
def average_salary_by_dept(df: pd.DataFrame, active_only=True) -> pd.Series:
    """
    Return mean salary per department, descending order.
    """
    if df is None or df.empty or "Department" not in df.columns or "Salary" not in df.columns:
        return pd.Series(dtype=float)
    if active_only and "Status" in df.columns:
        df = df[df["Status"] == "Active"]
    return df.groupby("Department")["Salary"].mean().sort_values(ascending=False)


# --------------------------
# FEEDBACK SUMMARY
# --------------------------
def feedback_summary(feedback_df: pd.DataFrame, employee_df: pd.DataFrame):
    """
    Return feedback summary: Avg Rating & Feedback Count per employee.
    """
    if feedback_df is None or feedback_df.empty or employee_df is None or employee_df.empty:
        return pd.DataFrame(columns=["Employee", "Avg_Rating", "Feedback_Count"])
    
    summary = feedback_df.groupby("receiver_id").agg(
        Avg_Rating=("rating", "mean"),
        Feedback_Count=("rating", "count")
    ).reset_index()
    
    emp_map = employee_df.set_index("Emp_ID")["Name"].to_dict()
    summary["Employee"] = summary["receiver_id"].map(emp_map).fillna("Unknown")
    summary = summary[["Employee", "Avg_Rating", "Feedback_Count"]]
    return summary


# --------------------------
# MOOD TREND ANALYTICS
# --------------------------
def mood_trend(df: pd.DataFrame, freq="W"):
    """
    Return mood counts aggregated by week ('W') or month ('M').
    df: mood logs with columns: emp_id, mood, log_date
    freq: 'W' for weekly, 'M' for monthly
    """
    if df is None or df.empty or "log_date" not in df.columns or "mood" not in df.columns:
        return pd.DataFrame(columns=["Period", "Mood", "Count"])
    
    df = df.copy()
    df["log_date"] = pd.to_datetime(df["log_date"], errors="coerce")
    df["Period"] = df["log_date"].dt.to_period(freq).astype(str)
    
    trend = df.groupby(["Period", "mood"]).size().reset_index(name="Count")
    return trend


# --------------------------
# TASK SUMMARY
# --------------------------
def task_summary(task_df: pd.DataFrame):
    """
    Return task counts by status and priority.
    """
    if task_df is None or task_df.empty:
        return pd.DataFrame(columns=["Status", "Priority", "Count"])
    
    df = task_df.copy()
    df["status"] = df.get("status", "Unknown")
    df["priority"] = df.get("priority", "Normal")
    summary = df.groupby(["status", "priority"]).size().reset_index(name="Count")
    return summary


# --------------------------
# EMPLOYEE OPTIONS FOR FORMS
# --------------------------
def employee_options(df: pd.DataFrame):
    """
    Return list of strings: "Emp_ID - Name"
    """
    if df is None or df.empty or "Emp_ID" not in df.columns or "Name" not in df.columns:
        return []
    return (df["Emp_ID"].astype(str) + " - " + df["Name"]).tolist()


# --------------------------
# DEPARTMENT OPTIONS
# --------------------------
def department_options(df: pd.DataFrame):
    """
    Return sorted list of unique departments.
    """
    if df is None or df.empty or "Department" not in df.columns:
        return []
    return sorted(df["Department"].dropna().unique())


# --------------------------
# ROLE OPTIONS
# --------------------------
def role_options(df: pd.DataFrame):
    """
    Return sorted list of unique roles.
    """
    if df is None or df.empty or "Role" not in df.columns:
        return []
    return sorted(df["Role"].dropna().unique())


# --------------------------
# SKILL OPTIONS
# --------------------------
def skill_options(df: pd.DataFrame):
    """
    Return sorted unique skills from 'Skills' column (comma or semicolon separated).
    """
    if df is None or df.empty or "Skills" not in df.columns:
        return []
    all_skills = df["Skills"].dropna().str.replace(";", ",").str.split(",").explode().str.strip()
    return sorted(all_skills.unique())
