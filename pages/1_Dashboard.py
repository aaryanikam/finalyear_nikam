# pages/1_Dashboard.py
"""
Dashboard — Workforce Analytics System
- FIXED: Key Metrics now show correct numbers (dict unpacking bug fixed)
- ADDED: Hover effects on all charts using Plotly
- KEPT: All original graph formats and structure
- PDF export with graph
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import io

from utils import database as db
from utils.analytics import (
    get_summary,
    department_distribution,
    gender_ratio,
    average_salary_by_dept
)
from utils.pdf_export import generate_master_report

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# -------------------------
# Custom CSS for metric cards with hover
# -------------------------
st.markdown("""
<style>
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    padding: 20px;
    color: white;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
[data-testid="metric-container"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(102,126,234,0.4);
}
[data-testid="metric-container"] > div {
    color: white !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: rgba(255,255,255,0.85) !important;
    font-size: 14px !important;
    font-weight: 600 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: white !important;
    font-size: 36px !important;
    font-weight: 800 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Workforce Dashboard")

# -------------------------
# Load employee data
# -------------------------
try:
    df = db.fetch_employees()
except Exception as e:
    st.error("Failed to fetch employee data.")
    st.exception(e)
    df = pd.DataFrame()

# -------------------------
# Key Metrics  ← FIXED: get_summary returns dict, extract values properly
# -------------------------
st.header("1️⃣ Key Metrics")

if not df.empty:
    summary = get_summary(df)
    # Handle both dict and tuple return (defensive)
    if isinstance(summary, dict):
        total    = summary.get("total", 0)
        active   = summary.get("active", 0)
        resigned = summary.get("resigned", 0)
    else:
        # fallback if someone changed get_summary to return tuple
        total, active, resigned = summary
else:
    total, active, resigned = 0, 0, 0

# Extra metrics computed directly for accuracy
dept_count   = df["Department"].nunique() if not df.empty else 0
avg_salary   = int(df["Salary"].mean()) if not df.empty and "Salary" in df.columns else 0
retention    = round((active / total * 100), 1) if total > 0 else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("👥 Total Employees",   total)
col2.metric("✅ Active Employees",  active)
col3.metric("🚪 Resigned",          resigned)
col4.metric("🏢 Departments",       dept_count)
col5.metric("💰 Avg Salary",        f"₹{avg_salary:,}")

st.divider()

# -------------------------
# Department Distribution  ← PLOTLY (hover enabled)
# -------------------------
st.header("2️⃣ Department Distribution")

dashboard_png = None  # for PDF

if not df.empty and "Department" in df.columns:
    dept_counts = department_distribution(df)

    # --- Plotly interactive chart (hover) ---
    fig_plotly = go.Figure(go.Bar(
        x=dept_counts.index.tolist(),
        y=dept_counts.values.tolist(),
        text=dept_counts.values.tolist(),
        textposition="outside",
        marker=dict(
            color=dept_counts.values.tolist(),
            colorscale="Blues",
            showscale=False,
            line=dict(color="rgba(0,0,0,0.2)", width=1)
        ),
        hovertemplate="<b>%{x}</b><br>Employees: %{y}<extra></extra>"
    ))
    fig_plotly.update_layout(
        title="Employees by Department",
        xaxis_title="Department",
        yaxis_title="Count",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#667eea", font_color="white"),
        height=420
    )
    st.plotly_chart(fig_plotly, use_container_width=True)

    # --- Matplotlib version for PDF only (not displayed) ---
    fig_pdf, ax_pdf = plt.subplots(figsize=(10, 5))
    bars = ax_pdf.bar(dept_counts.index, dept_counts.values)
    ax_pdf.set_title("Employees by Department")
    ax_pdf.set_xlabel("Department")
    ax_pdf.set_ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    for bar in bars:
        ax_pdf.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(int(bar.get_height())),
            ha="center", va="bottom", fontsize=9
        )
    plt.tight_layout()
    buf = io.BytesIO()
    fig_pdf.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    dashboard_png = buf.read()
    plt.close(fig_pdf)
else:
    st.info("No department data available.")

# -------------------------
# Skill Distribution  ← PLOTLY (hover enabled)
# -------------------------
st.header("3️⃣ Skill Distribution")

if not df.empty and "Skills" in df.columns:
    skill_list = []
    for s in df["Skills"].dropna():
        parts = s.replace(";", ",").split(",")
        for p in parts:
            clean = p.split(":")[0].strip()   # strip :level suffix
            if clean:
                skill_list.append(clean)

    if skill_list:
        skill_counts = pd.Series(skill_list).value_counts().head(15)

        fig_skill = go.Figure(go.Bar(
            x=skill_counts.index.tolist(),
            y=skill_counts.values.tolist(),
            text=skill_counts.values.tolist(),
            textposition="outside",
            marker=dict(
                color=skill_counts.values.tolist(),
                colorscale="Teal",
                showscale=False
            ),
            hovertemplate="<b>%{x}</b><br>Employees: %{y}<extra></extra>"
        ))
        fig_skill.update_layout(
            title="Top Skills Across Workforce",
            xaxis_title="Skills",
            yaxis_title="Count",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(bgcolor="#2dd4bf", font_color="white"),
            height=420
        )
        st.plotly_chart(fig_skill, use_container_width=True)
    else:
        st.info("No skill data available.")
else:
    st.info("No skill data available.")

# -------------------------
# Gender Ratio  ← PLOTLY PIE (hover enabled)
# -------------------------
st.header("4️⃣ Gender Ratio")

if not df.empty and "Gender" in df.columns:
    gender_counts = gender_ratio(df)

    col_g1, col_g2 = st.columns([1, 1])

    with col_g1:
        fig_gender = go.Figure(go.Pie(
            labels=gender_counts.index.tolist(),
            values=gender_counts.values.tolist(),
            hole=0.4,
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
            marker=dict(colors=["#667eea", "#f472b6"],
                        line=dict(color="white", width=2))
        ))
        fig_gender.update_layout(
            title="Gender Distribution",
            showlegend=True,
            height=380,
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_gender, use_container_width=True)

    with col_g2:
        # Gender breakdown by department
        if "Department" in df.columns:
            gender_dept = df.groupby(["Department", "Gender"]).size().reset_index(name="Count")
            fig_gd = px.bar(
                gender_dept, x="Department", y="Count", color="Gender",
                barmode="group",
                title="Gender by Department",
                color_discrete_map={"Male": "#667eea", "Female": "#f472b6"},
                hover_data={"Count": True}
            )
            fig_gd.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=380
            )
            st.plotly_chart(fig_gd, use_container_width=True)
else:
    st.info("No gender data available.")

# -------------------------
# Average Salary by Department  ← PLOTLY (hover enabled)
# -------------------------
st.header("5️⃣ Average Salary by Department")

if not df.empty and "Department" in df.columns and "Salary" in df.columns:
    avg_salary_dept = average_salary_by_dept(df)

    fig_sal = go.Figure(go.Bar(
        x=avg_salary_dept.index.tolist(),
        y=avg_salary_dept.values.tolist(),
        text=[f"₹{int(v):,}" for v in avg_salary_dept.values],
        textposition="outside",
        marker=dict(
            color=avg_salary_dept.values.tolist(),
            colorscale="Oranges",
            showscale=False
        ),
        hovertemplate="<b>%{x}</b><br>Avg Salary: ₹%{y:,.0f}<extra></extra>"
    ))
    fig_sal.update_layout(
        title="Average Salary by Department",
        xaxis_title="Department",
        yaxis_title="Avg Salary (₹)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#f97316", font_color="white"),
        height=420
    )
    st.plotly_chart(fig_sal, use_container_width=True)
else:
    st.info("No salary data available.")

# -------------------------
# Status Breakdown  ← NEW mini section
# -------------------------
st.header("6️⃣ Employee Status Breakdown")

if not df.empty and "Status" in df.columns:
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        status_counts = df["Status"].value_counts()
        fig_status = go.Figure(go.Pie(
            labels=status_counts.index.tolist(),
            values=status_counts.values.tolist(),
            hole=0.5,
            hovertemplate="<b>%{label}</b><br>%{value} employees (%{percent})<extra></extra>",
            marker=dict(colors=["#22c55e", "#ef4444"],
                        line=dict(color="white", width=2))
        ))
        fig_status.update_layout(
            title="Active vs Resigned",
            height=320,
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col_s2:
        # Retention rate card
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #22c55e, #16a34a);
             border-radius: 14px; padding: 30px; text-align: center; color: white; height: 280px;
             display: flex; flex-direction: column; justify-content: center;'>
            <div style='font-size: 16px; opacity: 0.9; margin-bottom: 8px;'>🏆 Retention Rate</div>
            <div style='font-size: 64px; font-weight: 900; letter-spacing: -2px;'>{retention}%</div>
            <div style='font-size: 13px; opacity: 0.75; margin-top: 8px;'>
                {active} active out of {total} total employees
            </div>
        </div>
        """, unsafe_allow_html=True)

# -------------------------
# Recent Employees
# -------------------------
st.header("7️⃣ Recent Employees")

if not df.empty and "Join_Date" in df.columns:
    recent_df = df.sort_values(by="Join_Date", ascending=False).head(10).reset_index(drop=True)
    recent_df.insert(0, "Sr No", range(1, len(recent_df) + 1))
    st.dataframe(
        recent_df[["Sr No", "Emp_ID", "Name", "Department", "Role", "Join_Date", "Status"]],
        use_container_width=True
    )
else:
    st.info("No employee data available.")

# -------------------------
# PDF EXPORT (WITH GRAPH)
# -------------------------
st.divider()
st.subheader("📄 Download Dashboard PDF")

if st.button("Download Dashboard PDF"):
    if dashboard_png is None:
        st.error("No graph available to export.")
    else:
        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=df,
                attendance_df=None,
                mood_df=None,
                projects_df=None,
                notifications_df=None,
                dashboard_fig=dashboard_png
            )
            pdf_buffer.seek(0)
            st.download_button(
                "⬇️ Download PDF",
                pdf_buffer,
                "dashboard_report.pdf",
                "application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)