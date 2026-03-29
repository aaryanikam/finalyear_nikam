# pages/13_Email_Notifications.py
"""
Email Notifications Center — Workforce Intelligence System
- Send emails to individual employees or entire departments
- Email templates for common HR events
- Track sent email history
- Role-based access (Admin / HR only)
"""

import streamlit as st
import pandas as pd
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

# -------------------------
# Page Config & Auth
# -------------------------
st.set_page_config(page_title="Email Notifications", page_icon="📧", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

if role not in ["Admin", "HR"]:
    st.warning("⚠️ Access denied. Admin and HR only.")
    st.stop()

st.title("📧 Email Notification Center")
st.caption("Send HR emails, alerts, and announcements to employees")

# -------------------------
# Load Employees
# -------------------------
try:
    emp_df = db.fetch_employees()
except Exception:
    emp_df = pd.DataFrame(columns=["Emp_ID", "Name", "Department", "Role", "Status"])

# -------------------------
# SMTP Configuration (Sidebar)
# -------------------------
st.sidebar.header("⚙️ SMTP Configuration")
st.sidebar.info("Configure your email server credentials to send real emails.")

smtp_host = st.sidebar.text_input("SMTP Host", value="smtp.gmail.com", placeholder="smtp.gmail.com")
smtp_port = st.sidebar.number_input("SMTP Port", value=587, min_value=1, max_value=9999)
sender_email = st.sidebar.text_input("Sender Email", placeholder="your@gmail.com")
sender_password = st.sidebar.text_input("App Password", type="password", placeholder="Google App Password")

smtp_configured = bool(sender_email and sender_password)

if not smtp_configured:
    st.info(
        "💡 **Setup Guide:** Enter your SMTP credentials in the sidebar. "
        "For Gmail, create an **App Password** at myaccount.google.com → Security → App passwords. "
        "Emails will be sent in **preview mode** until configured."
    )

# -------------------------
# Email Templates
# -------------------------
EMAIL_TEMPLATES = {
    "Custom Message": {
        "subject": "",
        "body": ""
    },
    "Welcome Onboard": {
        "subject": "Welcome to the Team! 🎉",
        "body": """Dear {name},

We are thrilled to welcome you to our team at {department}!

Your journey begins today and we are confident you will make a great contribution as {role}.

Please don't hesitate to reach out to HR if you need any assistance settling in.

Warm regards,
HR Team"""
    },
    "Performance Review Reminder": {
        "subject": "Performance Review Scheduled",
        "body": """Dear {name},

This is a reminder that your annual performance review is scheduled.

Please prepare your self-assessment and be ready to discuss your achievements, challenges, and goals for the upcoming year.

Your manager will reach out to confirm the date and time.

Best regards,
HR Team"""
    },
    "Attendance Warning": {
        "subject": "Attendance Concern — Action Required",
        "body": """Dear {name},

We have noticed a pattern of irregular attendance in your recent records.

Consistent attendance is essential for team productivity and we kindly request you to ensure timely check-ins going forward.

If you are facing any personal challenges, please speak to your HR representative confidentially.

Regards,
HR Department"""
    },
    "Resignation Acknowledgement": {
        "subject": "Resignation Acknowledgement",
        "body": """Dear {name},

We have received your resignation and acknowledge your decision to move on from your role as {role} in the {department} department.

Your last working day will be confirmed shortly. We wish you all the best in your future endeavours.

Thank you for your contributions to the team.

Sincerely,
HR Team"""
    },
    "Salary Credited": {
        "subject": "Salary Credited for This Month",
        "body": """Dear {name},

We are pleased to inform you that your salary for this month has been processed and credited to your registered bank account.

For any payroll queries, please contact HR or Finance.

Regards,
Payroll Team"""
    },
    "Task Deadline Reminder": {
        "subject": "Upcoming Task Deadline Reminder",
        "body": """Dear {name},

This is a friendly reminder that you have tasks approaching their deadline.

Please log in to the Workforce System to review your pending tasks and update their status.

Let your manager know if you need any support.

Best,
{sent_by}"""
    },
    "Happy Birthday! 🎂": {
        "subject": "Happy Birthday from the Team! 🎂",
        "body": """Dear {name},

Wishing you a very Happy Birthday from the entire team! 🎉🎂

May this special day bring you joy, laughter, and all the success you deserve.

With warm wishes,
HR Team & Your Colleagues"""
    }
}

# -------------------------
# Compose Email Tab Layout
# -------------------------
tab1, tab2 = st.tabs(["✉️ Compose & Send", "📜 Sent History"])

with tab1:

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📝 Compose Email")

        # Template picker
        template_choice = st.selectbox("📋 Load Template", list(EMAIL_TEMPLATES.keys()))
        template = EMAIL_TEMPLATES[template_choice]

        # Recipient mode
        recipient_mode = st.radio(
            "Send To",
            ["Individual Employee", "Entire Department", "All Active Employees"],
            horizontal=True
        )

        recipient_emails_raw = []
        recipient_names = []

        if recipient_mode == "Individual Employee" and not emp_df.empty:
            emp_options = (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist()
            selected_emp = st.selectbox("Select Employee", emp_options)
            emp_id_sel = int(selected_emp.split(" - ")[0])
            emp_row = emp_df[emp_df["Emp_ID"] == emp_id_sel].iloc[0]
            recipient_emails_raw = [f"{emp_row['Name'].lower().replace(' ', '.')}@company.com"]
            recipient_names = [emp_row["Name"]]
            st.info(f"📌 Simulated email: `{recipient_emails_raw[0]}`")

        elif recipient_mode == "Entire Department" and not emp_df.empty:
            depts = sorted(emp_df["Department"].dropna().unique())
            selected_dept = st.selectbox("Select Department", depts)
            dept_emps = emp_df[emp_df["Department"] == selected_dept]
            recipient_emails_raw = [
                f"{n.lower().replace(' ', '.')}@company.com"
                for n in dept_emps["Name"]
            ]
            recipient_names = dept_emps["Name"].tolist()
            st.info(f"📌 {len(recipient_emails_raw)} employees in **{selected_dept}**")

        elif recipient_mode == "All Active Employees" and not emp_df.empty:
            active_emps = emp_df[emp_df["Status"] == "Active"]
            recipient_emails_raw = [
                f"{n.lower().replace(' ', '.')}@company.com"
                for n in active_emps["Name"]
            ]
            recipient_names = active_emps["Name"].tolist()
            st.info(f"📌 {len(recipient_emails_raw)} active employees will receive this email")

        # Override recipient email (optional)
        custom_email = st.text_input(
            "Override Recipient Email (optional)",
            placeholder="Enter real email to actually deliver"
        )

        st.divider()

        # Compose
        subject = st.text_input("Subject", value=template["subject"])

        # Auto-fill first recipient name in template
        first_name = recipient_names[0] if recipient_names else "Employee"
        dept_name = ""
        role_name = ""
        if recipient_mode == "Individual Employee" and not emp_df.empty and recipient_names:
            emp_row_sel = emp_df[emp_df["Name"] == first_name].iloc[0] if first_name in emp_df["Name"].values else None
            dept_name = emp_row_sel["Department"] if emp_row_sel is not None else ""
            role_name = emp_row_sel["Role"] if emp_row_sel is not None else ""

        prefilled_body = template["body"].format(
            name=first_name,
            department=dept_name or "[Department]",
            role=role_name or "[Role]",
            sent_by=username
        ) if template["body"] else ""

        body = st.text_area("Email Body", value=prefilled_body, height=300)

        send_btn = st.button("🚀 Send Email", use_container_width=True, type="primary")

    with col_right:
        st.subheader("👀 Email Preview")

        if subject or body:
            st.markdown(
                f"""
                <div style='border: 1px solid #ddd; border-radius: 10px; padding: 20px; background: #fafafa;'>
                    <div style='font-size: 13px; color: #888;'>From: <b>{sender_email or "hr@company.com"}</b></div>
                    <div style='font-size: 13px; color: #888;'>To: <b>{', '.join(recipient_emails_raw[:3]) + ('...' if len(recipient_emails_raw) > 3 else '') if recipient_emails_raw else 'No recipients'}</b></div>
                    <hr style='margin: 10px 0;'>
                    <div style='font-size: 16px; font-weight: bold; margin-bottom: 12px;'>📨 {subject or "(No subject)"}</div>
                    <div style='font-size: 14px; white-space: pre-wrap; color: #333;'>{body or "(No body)"}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info("Fill in the subject and body to see a preview here.")

        st.divider()
        st.subheader("📊 Quick Stats")
        c1, c2, c3 = st.columns(3)
        c1.metric("Recipients", len(recipient_emails_raw))
        c2.metric("Total Employees", len(emp_df))
        c3.metric("Active Employees", len(emp_df[emp_df["Status"] == "Active"]) if not emp_df.empty else 0)

    # -------------------------
    # Send Logic
    # -------------------------
    if send_btn:
        if not subject.strip() or not body.strip():
            st.error("❌ Subject and body cannot be empty.")
        elif not recipient_emails_raw:
            st.error("❌ No recipients selected.")
        else:
            # Determine actual target email
            targets = [custom_email] if custom_email.strip() else recipient_emails_raw

            if smtp_configured:
                # Real send
                success_count = 0
                fail_count = 0

                progress = st.progress(0)
                status_text = st.empty()

                for i, (email, name) in enumerate(zip(targets, recipient_names if not custom_email else [first_name] * len(targets))):
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = subject
                        msg["From"] = sender_email
                        msg["To"] = email

                        personal_body = body.replace("{name}", name)
                        part = MIMEText(personal_body, "plain")
                        msg.attach(part)

                        context = ssl.create_default_context()
                        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                            server.ehlo()
                            server.starttls(context=context)
                            server.login(sender_email, sender_password)
                            server.sendmail(sender_email, email, msg.as_string())

                        success_count += 1

                    except Exception as e:
                        fail_count += 1

                    progress.progress((i + 1) / len(targets))
                    status_text.text(f"Sending... {i+1}/{len(targets)}")

                progress.empty()
                status_text.empty()

                if success_count:
                    st.success(f"✅ {success_count} email(s) sent successfully!")
                if fail_count:
                    st.warning(f"⚠️ {fail_count} email(s) failed. Check SMTP settings.")

                # Log to session history
                if "email_history" not in st.session_state:
                    st.session_state["email_history"] = []

                st.session_state["email_history"].append({
                    "Sent At": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Subject": subject,
                    "Recipients": len(targets),
                    "Mode": recipient_mode,
                    "Sent By": username,
                    "Status": f"✅ {success_count} sent / ❌ {fail_count} failed"
                })

            else:
                # Preview mode
                st.warning(
                    "📬 **Preview Mode** — SMTP not configured. "
                    "The email below would be sent to recipients once configured."
                )

                with st.expander("📨 Email That Would Be Sent", expanded=True):
                    st.code(
                        f"TO: {', '.join(targets[:5])}{'...' if len(targets) > 5 else ''}\n"
                        f"SUBJECT: {subject}\n\n{body}",
                        language="text"
                    )

                # Still log to history
                if "email_history" not in st.session_state:
                    st.session_state["email_history"] = []

                st.session_state["email_history"].append({
                    "Sent At": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Subject": subject,
                    "Recipients": len(targets),
                    "Mode": recipient_mode,
                    "Sent By": username,
                    "Status": "📬 Preview Only"
                })

                st.info(
                    "💡 To send real emails: add your Gmail + App Password in the sidebar. "
                    "No code changes needed!"
                )


with tab2:
    st.subheader("📜 Email Sent History")

    history = st.session_state.get("email_history", [])

    if history:
        hist_df = pd.DataFrame(history[::-1])  # newest first
        st.dataframe(hist_df, use_container_width=True)

        # Stats
        st.divider()
        st.subheader("📊 Email Analytics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Emails Sent", len(history))
        total_recipients = sum(h["Recipients"] for h in history)
        c2.metric("Total Recipients Reached", total_recipients)
        preview_count = sum(1 for h in history if "Preview" in str(h["Status"]))
        c3.metric("Preview Mode Emails", preview_count)

        import matplotlib.pyplot as plt
        mode_counts = pd.Series([h["Mode"] for h in history]).value_counts()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.bar(mode_counts.index, mode_counts.values)
        ax.set_title("Emails by Recipient Mode")
        ax.set_ylabel("Count")
        plt.xticks(rotation=15, ha="right")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        if st.button("🗑️ Clear History"):
            st.session_state["email_history"] = []
            st.rerun()
    else:
        st.info("No emails sent yet this session.")