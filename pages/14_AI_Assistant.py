# pages/14_AI_Assistant.py
"""
AI Workforce Assistant — Powered by Google Gemini (FREE)
Get key at: https://aistudio.google.com — No credit card needed
"""

import streamlit as st
import pandas as pd
import requests
import datetime

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
st.title("🤖 AI Workforce Assistant")
st.caption("Powered by **Google Gemini** — 100% Free, no credit card needed")

# ─────────────────────────────────────────────
# Sidebar — API Key
# ─────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### 🔑 Gemini API Key")
st.sidebar.markdown("""
**Get FREE key in 2 minutes:**
1. 👉 [aistudio.google.com](https://aistudio.google.com)
2. Sign in with Gmail
3. Click **Get API Key** → Create → Copy

✅ No credit card. No payment.
✅ 15 requests/min free forever.
""")

api_key = st.sidebar.text_input(
    "Paste your Gemini API Key",
    type="password",
    placeholder="AIzaSy...",
    key="gemini_key"
)

model_choice = st.sidebar.selectbox(
    "Model",
    ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    help="2.0-flash is fastest and free. 1.5-pro is smarter."
)

# ─────────────────────────────────────────────
# Data context builder
# ─────────────────────────────────────────────
@st.cache_data(ttl=120)
def build_context():
    try:
        emp   = db.fetch_employees()
        att   = db.fetch_attendance()
        mood  = db.fetch_mood_logs()
        tasks = db.fetch_tasks()
        fb    = db.fetch_feedback()
        proj  = db.fetch_projects()
    except Exception:
        return "Workforce data unavailable."

    lines = [f"=== LIVE WORKFORCE DATA ({datetime.date.today()}) ==="]

    if not emp.empty:
        active = emp[emp['Status'] == 'Active']
        resigned = emp[emp['Status'] == 'Resigned']
        lines.append(f"Total employees: {len(emp)} ({len(active)} active, {len(resigned)} resigned)")
        dept = emp['Department'].value_counts().to_dict()
        lines.append("Departments: " + ", ".join(f"{k}={v}" for k, v in dept.items()))
        lines.append(f"Avg salary: ₹{emp['Salary'].mean():,.0f}")
        gender = emp['Gender'].value_counts().to_dict()
        lines.append(f"Gender: {gender}")

    if not att.empty:
        pr = len(att[att['status'] == 'Present'])
        lines.append(f"Attendance rate: {pr/len(att)*100:.1f}% ({pr}/{len(att)} present)")

    if not mood.empty:
        mood = mood.copy()
        mood['lbl'] = mood['mood_score'].apply(
            lambda x: 'Happy' if x >= 20 else ('Neutral' if x >= 13 else 'Stressed'))
        mc = mood['lbl'].value_counts().to_dict()
        lines.append(f"Mood: Happy={mc.get('Happy',0)}, Neutral={mc.get('Neutral',0)}, Stressed={mc.get('Stressed',0)}")
        stressed_ids = mood[mood['lbl'] == 'Stressed']['emp_id'].unique().tolist()
        lines.append(f"Stressed employee IDs: {stressed_ids[:10]}")

    if not tasks.empty:
        tc = tasks['status'].value_counts().to_dict()
        lines.append(f"Tasks: {tc}")
        overdue_count = 0
        try:
            tasks['due_dt'] = pd.to_datetime(tasks['due_date'], errors='coerce')
            overdue_count = len(tasks[
                (tasks['status'] != 'Completed') &
                (tasks['due_dt'] < pd.Timestamp.today())
            ])
        except Exception:
            pass
        lines.append(f"Overdue tasks: {overdue_count}")

    if not fb.empty:
        lines.append(f"Feedback: {len(fb)} entries, avg rating {fb['rating'].mean():.1f}/5")

    if not proj.empty:
        lines.append(f"Projects: {proj['status'].value_counts().to_dict()}")
        lines.append(f"Avg progress: {proj['progress'].mean():.0f}%")

    return "\n".join(lines)


def call_gemini(api_key, model, messages):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")

    contents = []
    for m in messages:
        contents.append({
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": m["content"]}]
        })

    try:
        r = requests.post(url, json={
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
        }, timeout=30)

        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif r.status_code == 429:
            return "⚠️ Rate limit reached. Wait 1 minute and try again. (Free tier: 15 requests/min)"
        elif r.status_code == 403:
            return "❌ Invalid API key. Visit aistudio.google.com to get your free key."
        else:
            return f"❌ Error {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return f"❌ Connection error: {e}"


# ─────────────────────────────────────────────
# Show stats in sidebar
# ─────────────────────────────────────────────
try:
    st.sidebar.divider()
    st.sidebar.markdown("### 📊 Data Loaded")
    emp_df = db.fetch_employees()
    st.sidebar.metric("Employees", len(emp_df))
    st.sidebar.metric("Active",    len(emp_df[emp_df['Status'] == 'Active']) if not emp_df.empty else 0)
    st.sidebar.metric("Tasks",     len(db.fetch_tasks()))
    st.sidebar.metric("Projects",  len(db.fetch_projects()))
except Exception:
    pass

# ─────────────────────────────────────────────
# No key — show setup guide
# ─────────────────────────────────────────────
if not api_key:
    st.markdown("""
    ## 🆓 Get Your Free AI Key (Takes 2 Minutes)

    | Step | Action |
    |------|--------|
    | 1️⃣ | Open **[aistudio.google.com](https://aistudio.google.com)** |
    | 2️⃣ | Sign in with any **Gmail account** |
    | 3️⃣ | Click **"Get API Key"** in the left panel |
    | 4️⃣ | Click **"Create API key in new project"** |
    | 5️⃣ | **Copy** the key and paste in the sidebar |

    ### ✅ What you get for FREE:
    - **15 requests per minute** — plenty for a project
    - **1 million tokens per day** — very generous
    - **Gemini 2.0 Flash** — Google's fastest, smartest free model
    - **No credit card. No expiry. No hidden charges.**

    ### 🤖 What the AI can do for your project:
    - Summarise workforce health across all 200 employees
    - Identify attendance patterns and flag issues
    - Detect stressed employees from mood data
    - Suggest retention strategies based on attrition risk
    - Answer any HR question in plain English
    """)
    st.stop()

# ─────────────────────────────────────────────
# Chat interface
# ─────────────────────────────────────────────
SYSTEM = (
    "You are an expert HR Analytics AI for a Workforce Intelligence System. "
    "You have access to live workforce data below. Be specific, use numbers, "
    "and give actionable HR recommendations. Use Indian context (₹ for salary).\n\n"
    + build_context()
)

if "ai_chat" not in st.session_state:
    st.session_state.ai_chat = []

# Quick action buttons
st.subheader("⚡ Quick Questions")
cols = st.columns(4)
quick = [
    ("📊", "Summarise overall workforce health"),
    ("⚠️", "List employees with poor attendance"),
    ("😟", "Which employees seem stressed?"),
    ("🚨", "Which projects are at risk or overdue?"),
    ("💰", "Compare salaries across departments"),
    ("🔄", "Who is at risk of resigning?"),
    ("📋", "How is task completion across the team?"),
    ("🏆", "Who are the top performers?"),
]
for i, (emoji, text) in enumerate(quick):
    if cols[i % 4].button(f"{emoji} {text}", use_container_width=True, key=f"q{i}"):
        st.session_state.ai_chat.append({"role": "user", "content": text})
        st.rerun()

st.divider()

# Display history
for msg in st.session_state.ai_chat:
    with st.chat_message("user" if msg["role"] == "user" else "assistant",
                         avatar=None if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

# Input
prompt = st.chat_input("Ask anything about your workforce...")

if prompt:
    st.session_state.ai_chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build messages: inject system into first user message
    to_send = []
    for i, m in enumerate(st.session_state.ai_chat):
        if i == 0 and m["role"] == "user":
            to_send.append({"role": "user", "content": SYSTEM + "\n\nUser: " + m["content"]})
        else:
            to_send.append(m)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Gemini is thinking..."):
            reply = call_gemini(api_key, model_choice, to_send)
        st.markdown(reply)

    st.session_state.ai_chat.append({"role": "assistant", "content": reply})

# Bottom controls
st.divider()
c1, c2 = st.columns(2)
if c1.button("🗑️ Clear Chat", use_container_width=True):
    st.session_state.ai_chat = []
    st.rerun()

if c2.button("📥 Export Chat as TXT", use_container_width=True):
    txt = "\n\n".join(
        f"{'YOU' if m['role']=='user' else 'GEMINI AI'}: {m['content']}"
        for m in st.session_state.ai_chat
    )
    st.download_button("⬇️ Download", txt.encode(), f"chat_{datetime.date.today()}.txt", "text/plain")