# utils/database.py
"""
Database utilities — Workforce Intelligence System
- SQLite backend
- Employee-linked login: username = full name, password = firstname123
- sys_role column on employees table (Admin / HR / Manager / Employee)
- All existing CRUD kept intact
"""

import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

DB_NAME = "workforce.db"


# ─────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────
def connect_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# ─────────────────────────────────────────────
# Password hashing
# ─────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def make_employee_password(full_name: str) -> str:
    """firstname123 — e.g. 'Aarti Sharma' → 'aarti123'"""
    first = full_name.strip().split()[0].lower()
    return first + "123"


# ─────────────────────────────────────────────
# Initialize All Tables
# ─────────────────────────────────────────────
def initialize_all_tables():
    conn = connect_db()
    cur  = conn.cursor()

    # users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role     TEXT
    )""")

    # employees table — sys_role column added
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        Emp_ID      INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        Name        TEXT,
        Age         INTEGER,
        Gender      TEXT,
        Department  TEXT,
        Role        TEXT,
        Skills      TEXT,
        Join_Date   TEXT,
        Resign_Date TEXT,
        Status      TEXT,
        Salary      REAL,
        Location    TEXT,
        sys_role    TEXT DEFAULT 'Employee'
    )""")

    # Add sys_role column to existing DBs that don't have it yet
    try:
        cur.execute("ALTER TABLE employees ADD COLUMN sys_role TEXT DEFAULT 'Employee'")
    except Exception:
        pass  # column already exists — fine

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name   TEXT,
        emp_id      INTEGER,
        assigned_by TEXT,
        due_date    TEXT,
        priority    TEXT,
        status      TEXT,
        remarks     TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mood_logs (
        mood_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id     INTEGER,
        mood_score INTEGER,
        remarks    TEXT,
        log_date   TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id   INTEGER,
        receiver_id INTEGER,
        message     TEXT,
        rating      INTEGER,
        log_date    TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id        INTEGER,
        date          TEXT,
        check_in      TEXT,
        check_out     TEXT,
        status        TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        notif_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id     INTEGER,
        message    TEXT,
        type       TEXT DEFAULT 'General',
        is_read    INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name  TEXT,
        owner_emp_id  INTEGER,
        status        TEXT,
        progress      INTEGER DEFAULT 0,
        start_date    TEXT,
        due_date      TEXT
    )""")

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# Create / Sync User Accounts
# ─────────────────────────────────────────────
def create_default_admin():
    """Always ensure the master admin account exists."""
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            ("admin", hash_password("admin123"), "Admin")
        )
    conn.commit()
    conn.close()


def sync_employee_users():
    """
    For every Active employee, create a users row if one doesn't exist yet.
    username = employee full name  (unique — Emp_ID appended if duplicate)
    password = firstname123
    role     = employee's sys_role
    Also link employee.user_id → users.id
    """
    conn = connect_db()
    cur  = conn.cursor()

    cur.execute(
        "SELECT Emp_ID, Name, sys_role, user_id FROM employees WHERE Status='Active'"
    )
    rows = cur.fetchall()

    for emp_id, name, sys_role, existing_uid in rows:
        if not name:
            continue

        sys_role = sys_role or "Employee"
        password = hash_password(make_employee_password(name))
        username = name.strip()

        # Check if a user already linked to this emp_id exists
        cur.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        )
        existing = cur.fetchone()

        if existing:
            uid = existing[0]
            # Refresh role in case it changed
            cur.execute(
                "UPDATE users SET role=?, password=? WHERE id=?",
                (sys_role, password, uid)
            )
        else:
            # Disambiguate duplicate full names by appending Emp_ID
            test_name = username
            cur.execute("SELECT id FROM users WHERE username=?", (test_name,))
            if cur.fetchone():
                test_name = f"{username} ({emp_id})"
            try:
                cur.execute(
                    "INSERT INTO users (username, password, role) VALUES (?,?,?)",
                    (test_name, password, sys_role)
                )
                uid = cur.lastrowid
            except Exception:
                continue

        # Keep employee.user_id in sync
        if existing_uid != uid:
            cur.execute(
                "UPDATE employees SET user_id=? WHERE Emp_ID=?",
                (uid, emp_id)
            )

    conn.commit()
    conn.close()


def update_employee_sys_role(emp_id: int, sys_role: str):
    """Change an employee's system role and update their users row."""
    conn = connect_db()
    cur  = conn.cursor()

    cur.execute(
        "UPDATE employees SET sys_role=? WHERE Emp_ID=?",
        (sys_role, emp_id)
    )

    # Also update the linked users row
    cur.execute("SELECT user_id FROM employees WHERE Emp_ID=?", (emp_id,))
    row = cur.fetchone()
    if row and row[0]:
        cur.execute(
            "UPDATE users SET role=? WHERE id=?",
            (sys_role, row[0])
        )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def get_user_by_username(username: str):
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_emp_id_by_user_id(user_id: int):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("SELECT Emp_ID FROM employees WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def list_all_usernames():
    """Return sorted list of all usernames for login hints."""
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("SELECT username FROM users WHERE username != 'admin' ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


# ─────────────────────────────────────────────
# EMPLOYEES (CRUD)
# ─────────────────────────────────────────────
def add_employee(emp: dict):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO employees
        (Name, Age, Gender, Department, Role, Skills,
         Join_Date, Resign_Date, Status, Salary, Location, sys_role)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        emp.get("Name"),
        emp.get("Age"),
        emp.get("Gender"),
        emp.get("Department"),
        emp.get("Role"),
        emp.get("Skills"),
        emp.get("Join_Date"),
        emp.get("Resign_Date", ""),
        emp.get("Status", "Active"),
        emp.get("Salary", 0),
        emp.get("Location", ""),
        emp.get("sys_role", "Employee"),
    ))
    conn.commit()
    conn.close()

    # Auto-create their user account
    sync_employee_users()


def fetch_employees():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM employees", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def update_employee(emp_id: int, updates: dict):
    if not updates:
        return
    conn = connect_db()
    cur  = conn.cursor()
    for key, val in updates.items():
        cur.execute(f"UPDATE employees SET {key}=? WHERE Emp_ID=?", (val, emp_id))
    conn.commit()
    conn.close()

    # Sync users if name or sys_role changed
    if "Name" in updates or "sys_role" in updates:
        sync_employee_users()


def delete_employee(emp_id: int):
    conn = connect_db()
    cur  = conn.cursor()

    # Remove linked user account (but never delete admin)
    cur.execute("SELECT user_id FROM employees WHERE Emp_ID=?", (emp_id,))
    row = cur.fetchone()
    if row and row[0]:
        cur.execute(
            "DELETE FROM users WHERE id=? AND username != 'admin'",
            (row[0],)
        )

    cur.execute("DELETE FROM employees WHERE Emp_ID=?", (emp_id,))
    conn.commit()
    conn.close()


def bulk_add_employees(df: pd.DataFrame):
    for _, row in df.iterrows():
        add_employee(row.to_dict())


# ─────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────
def add_task(task: dict):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO tasks
        (task_name, emp_id, assigned_by, due_date, priority, status, remarks)
        VALUES (?,?,?,?,?,?,?)
    """, (
        task["task_name"], task["emp_id"], task["assigned_by"],
        task["due_date"],  task["priority"], task["status"], task["remarks"]
    ))
    conn.commit()
    conn.close()


def fetch_tasks():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM tasks", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def update_task(task_id: int, updates: dict):
    conn = connect_db()
    cur  = conn.cursor()
    for key, val in updates.items():
        cur.execute(f"UPDATE tasks SET {key}=? WHERE task_id=?", (val, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id: int):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# MOOD
# ─────────────────────────────────────────────
def add_mood_entry(emp_id: int, mood_score: int, remarks=""):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO mood_logs (emp_id, mood_score, remarks, log_date) VALUES (?,?,?,?)",
        (emp_id, mood_score, remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def fetch_mood_logs():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM mood_logs", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# ─────────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────────
def add_feedback(sender_id, receiver_id, message, rating):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO feedback (sender_id,receiver_id,message,rating,log_date) VALUES (?,?,?,?,?)",
        (sender_id, receiver_id, message, rating, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def fetch_feedback():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM feedback", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def update_feedback(feedback_id, message, rating):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE feedback SET message=?, rating=? WHERE feedback_id=?",
        (message, rating, feedback_id)
    )
    conn.commit()
    conn.close()


def delete_feedback(feedback_id):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM feedback WHERE feedback_id=?", (feedback_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────────
def add_attendance(emp_id, date, check_in, check_out, status):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (emp_id,date,check_in,check_out,status) VALUES (?,?,?,?,?)",
        (emp_id, date, check_in, check_out, status)
    )
    conn.commit()
    conn.close()


def fetch_attendance(emp_id=None):
    conn = connect_db()
    try:
        if emp_id:
            df = pd.read_sql(
                "SELECT * FROM attendance WHERE emp_id=?", conn, params=(emp_id,)
            )
        else:
            df = pd.read_sql("SELECT * FROM attendance", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def bulk_add_attendance(df: pd.DataFrame):
    conn = connect_db()
    cur  = conn.cursor()
    for _, row in df.iterrows():
        cur.execute(
            "INSERT INTO attendance (emp_id,date,check_in,check_out,status) VALUES (?,?,?,?,?)",
            (row["emp_id"], row["date"], row["check_in"], row["check_out"], row["status"])
        )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────
def add_notification(emp_id, message, notif_type="General"):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (emp_id,message,type,created_at) VALUES (?,?,?,?)",
        (emp_id, message, notif_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def fetch_notifications(emp_id=None):
    conn = connect_db()
    try:
        if emp_id:
            df = pd.read_sql(
                """SELECT notif_id AS id, emp_id, message, type, is_read, created_at
                   FROM notifications WHERE emp_id=? ORDER BY created_at DESC""",
                conn, params=(emp_id,)
            )
        else:
            df = pd.read_sql(
                """SELECT notif_id AS id, emp_id, message, type, is_read, created_at
                   FROM notifications ORDER BY created_at DESC""",
                conn
            )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def mark_notification_read(notif_id):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("UPDATE notifications SET is_read=1 WHERE notif_id=?", (notif_id,))
    conn.commit()
    conn.close()


def delete_notification(notif_id):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM notifications WHERE notif_id=?", (notif_id,))
    conn.commit()
    conn.close()


def bulk_add_notifications(df: pd.DataFrame):
    conn = connect_db()
    cur  = conn.cursor()
    for _, row in df.iterrows():
        cur.execute(
            "INSERT INTO notifications (emp_id,message,type,is_read,created_at) VALUES (?,?,?,?,?)",
            (row["emp_id"], row["message"], row["type"], row["is_read"], row["created_at"])
        )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# PROJECTS
# ─────────────────────────────────────────────
def add_project(proj: dict):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO projects (project_name,owner_emp_id,status,progress,start_date,due_date)
        VALUES (?,?,?,?,?,?)
    """, (
        proj.get("project_name"), proj.get("owner_emp_id"),
        proj.get("status","Active"), proj.get("progress",0),
        proj.get("start_date",""), proj.get("due_date","")
    ))
    conn.commit()
    conn.close()


def fetch_projects():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM projects", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def update_project(project_id: int, updates: dict):
    conn = connect_db()
    cur  = conn.cursor()
    for key, val in updates.items():
        cur.execute(f"UPDATE projects SET {key}=? WHERE project_id=?", (val, project_id))
    conn.commit()
    conn.close()


def delete_project(project_id: int):
    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM projects WHERE project_id=?", (project_id,))
    conn.commit()
    conn.close()