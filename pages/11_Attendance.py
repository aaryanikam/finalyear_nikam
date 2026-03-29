# pages/11_Attendance.py
"""
Employee Attendance Tracker — Workforce Intelligence System
- Consistent sidebar
- Plotly interactive charts with hover
- Per-employee attendance rate
- CSV import
- PDF export
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

st.set_page_config(page_title="Attendance", page_icon="📋", layout="wide")
require_login()
show_role_badge()
logout_user()

role      = st.session_state.get("role", "Employee")
my_emp_id = st.session_state.get("my_emp_id")

st.title("📋 Employee Attendance Tracker")

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────
try:
    emp_df = db.fetch_employees()
except Exception:
    emp_df = pd.DataFrame(columns=["Emp_ID","Name","Status"])

try:
    attendance_df = db.fetch_attendance()
except Exception:
    attendance_df = pd.DataFrame(columns=["emp_id","date","check_in","check_out","status"])

emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict() if not emp_df.empty else {}

# ─────────────────────────────────────────────
# Employee Selection
# ─────────────────────────────────────────────
if role in ["Admin", "Manager", "HR"]:
    emp_options = ["All"] + (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist()
    selected    = st.selectbox("👤 Select Employee", emp_options)
    emp_id_sel  = None if selected == "All" else int(selected.split(" — ")[0])
else:
    emp_id_sel = my_emp_id
    selected   = "Mine"

# ─────────────────────────────────────────────
# Log Attendance (Admin only)
# ─────────────────────────────────────────────
if role == "Admin":
    with st.expander("⏰ Log Attendance", expanded=False):
        with st.form("log_attendance_form"):
            col1, col2, col3 = st.columns(3)
            log_emp  = col1.selectbox("Employee",
                                      (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist()
                                      if not emp_df.empty else [])
            log_date = col2.date_input("Date", datetime.date.today())
            log_stat = col3.selectbox("Status", ["Present","Absent","Half-day","Remote"])
            col4, col5 = st.columns(2)
            ci = col4.time_input("Check-in",  datetime.time(9, 0))
            co = col5.time_input("Check-out", datetime.time(18, 0))
            log_btn = st.form_submit_button("📝 Log Attendance", use_container_width=True)

            if log_btn and log_emp:
                try:
                    eid = int(log_emp.split(" — ")[0])
                    db.add_attendance(
                        emp_id=eid,
                        date=log_date.strftime("%Y-%m-%d"),
                        check_in=ci.strftime("%H:%M:%S"),
                        check_out=co.strftime("%H:%M:%S"),
                        status=log_stat
                    )
                    attendance_df = db.fetch_attendance()
                    st.success("✅ Attendance logged.")
                    st.rerun()
                except Exception as e:
                    st.error("❌ Failed to log attendance."); st.exception(e)

# ─────────────────────────────────────────────
# Date Range Filter
# ─────────────────────────────────────────────
st.divider()
col_d1, col_d2 = st.columns(2)
start = col_d1.date_input("📅 Start Date", datetime.date.today() - datetime.timedelta(days=30))
end   = col_d2.date_input("📅 End Date",   datetime.date.today())

att_df = attendance_df.copy()
if emp_id_sel is not None:
    att_df = att_df[att_df["emp_id"] == emp_id_sel]

att_df["Date"] = pd.to_datetime(att_df["date"], errors="coerce")
att_df = att_df[
    (att_df["Date"] >= pd.to_datetime(start)) &
    (att_df["Date"] <= pd.to_datetime(end))
]

attendance_png = None

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────
if not att_df.empty:
    total_days   = len(att_df)
    present_days = len(att_df[att_df["status"] == "Present"])
    absent_days  = len(att_df[att_df["status"] == "Absent"])
    remote_days  = len(att_df[att_df["status"] == "Remote"])
    att_rate     = round(present_days / total_days * 100, 1) if total_days > 0 else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📅 Total Records",  total_days)
    k2.metric("✅ Present",         present_days)
    k3.metric("❌ Absent",          absent_days)
    k4.metric("🏠 Remote",          remote_days)
    k5.metric("📊 Attendance Rate", f"{att_rate}%")

    st.divider()

    # ─────────────────────────────────────────────
    # Attendance History Table
    # ─────────────────────────────────────────────
    st.subheader("📅 Attendance History")

    att_df["Employee"] = att_df["emp_id"].map(emp_map).fillna(att_df["emp_id"].astype(str))
    display_df = att_df[["Employee","Date","check_in","check_out","status"]].sort_values("Date", ascending=False)
    st.dataframe(display_df.rename(columns={"check_in":"Check In","check_out":"Check Out","status":"Status"}),
                 use_container_width=True, height=320)

    csv_att = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Export as CSV", csv_att, "attendance_export.csv", "text/csv")

    st.divider()

    # ─────────────────────────────────────────────
    # Attendance Analytics — Plotly
    # ─────────────────────────────────────────────
    st.subheader("📊 Attendance Analytics")

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        sc = att_df["status"].value_counts().reset_index()
        sc.columns = ["Status","Count"]
        att_colors = {"Present":"#22c55e","Absent":"#ef4444","Half-day":"#f59e0b","Remote":"#667eea"}
        fig1 = px.pie(sc, names="Status", values="Count", hole=0.45,
                      title="Attendance Status Distribution",
                      color="Status", color_discrete_map=att_colors)
        fig1.update_traces(hovertemplate="<b>%{label}</b><br>%{value} days (%{percent})<extra></extra>")
        fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=340)
        st.plotly_chart(fig1, use_container_width=True)

    with col_c2:
        # Attendance trend over time
        daily = att_df.copy()
        daily["DateOnly"]  = daily["Date"].dt.date
        daily["IsPresent"] = (daily["status"].isin(["Present","Remote"])).astype(int)
        trend = daily.groupby("DateOnly")["IsPresent"].mean().reset_index()
        trend.columns = ["Date","Attendance Rate"]
        trend["Attendance Rate"] = (trend["Attendance Rate"] * 100).round(1)

        fig2 = px.line(trend, x="Date", y="Attendance Rate", markers=True,
                       title="Daily Attendance Rate (%)",
                       color_discrete_sequence=["#22c55e"])
        fig2.add_hline(y=80, line_dash="dash", line_color="#f59e0b",
                       annotation_text="80% Target")
        fig2.update_layout(
            yaxis=dict(range=[0,105]),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=340
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Per-employee attendance rate (admin / manager / hr)
    if role in ["Admin","Manager","HR"] and selected == "All":
        st.subheader("👥 Attendance Rate by Employee")
        emp_att = att_df.copy()
        emp_att["IsPresent"] = emp_att["status"].isin(["Present","Remote"]).astype(int)
        emp_rate = emp_att.groupby("Employee")["IsPresent"].mean().reset_index()
        emp_rate.columns = ["Employee","Rate"]
        emp_rate["Rate %"] = (emp_rate["Rate"] * 100).round(1)
        emp_rate = emp_rate.sort_values("Rate %")

        fig3 = px.bar(emp_rate, x="Rate %", y="Employee", orientation="h",
                      text="Rate %",
                      title="Attendance Rate per Employee (%)",
                      color="Rate %",
                      color_continuous_scale=["#ef4444","#f59e0b","#22c55e"],
                      range_color=[50,100])
        fig3.add_vline(x=80, line_dash="dash", line_color="#f59e0b",
                       annotation_text="80% Target")
        fig3.update_traces(texttemplate="%{text}%", textposition="outside")
        fig3.update_layout(
            xaxis=dict(range=[0,115]),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=max(400, len(emp_rate)*22),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Matplotlib PNG for PDF
    sc2 = att_df["status"].value_counts()
    bar_colors = [att_colors.get(s,"#667eea") for s in sc2.index]
    fig_m, ax = plt.subplots(figsize=(7,4))
    bars = ax.bar(sc2.index, sc2.values, color=bar_colors)
    ax.set_title("Attendance Status Distribution"); ax.set_ylabel("Count")
    for bar in bars:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    buf = io.BytesIO()
    fig_m.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    attendance_png = buf.read()
    plt.close(fig_m)

else:
    st.info("No attendance records found for the selected criteria.")

# ─────────────────────────────────────────────
# PDF Export
# ─────────────────────────────────────────────
st.divider()
st.subheader("📄 Master Workforce Report PDF")

if role in ["Admin","Manager","HR"]:
    if st.button("🖨️ Download Master PDF"):
        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=display_df if not att_df.empty else attendance_df,
                mood_df=db.fetch_mood_logs(),
                projects_df=db.fetch_projects(),
                notifications_df=pd.DataFrame(),
                attendance_fig=attendance_png
            )
            pdf_buffer.seek(0)
            st.download_button("⬇️ Download PDF", pdf_buffer,
                               "attendance_report.pdf", "application/pdf")
        except Exception as e:
            st.error("❌ Failed to generate PDF."); st.exception(e)
else:
    st.info("PDF download available for Admin, Manager, HR only.")

# ─────────────────────────────────────────────
# CSV Import (sidebar)
# ─────────────────────────────────────────────
if role in ["Admin","Manager","HR"]:
    st.sidebar.divider()
    st.sidebar.subheader("📥 Import Attendance CSV")
    st.sidebar.caption("Columns: emp_id, date, check_in, check_out, status")
    uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"], key="att_csv")

    if uploaded:
        try:
            csv_df = pd.read_csv(uploaded)
            required = ["emp_id","date","check_in","check_out","status"]
            if all(c in csv_df.columns for c in required):
                db.bulk_add_attendance(csv_df)
                attendance_df = db.fetch_attendance()
                st.sidebar.success(f"✅ {len(csv_df)} records imported!")
                st.rerun()
            else:
                st.sidebar.error(f"Missing columns: {required}")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")