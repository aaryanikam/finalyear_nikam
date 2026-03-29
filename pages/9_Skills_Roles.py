# pages/9_Skills_Roles.py
"""
Skill Inventory & Role Mapping — Workforce Intelligence System
- Consistent sidebar
- Plotly interactive charts with hover
- Skill gap analysis
- Role suggestions
- PDF export with graph
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

st.set_page_config(page_title="Skills & Roles", page_icon="🧰", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
st.title("🧰 Skill Inventory & Role Mapping")

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────
try:
    emp_df = db.fetch_employees()
except Exception as e:
    st.error("❌ Failed to load employees.")
    st.exception(e)
    emp_df = pd.DataFrame()

if emp_df.empty:
    st.info("No employee data available.")
    st.stop()

# ─────────────────────────────────────────────
# Parse Skills helper
# ─────────────────────────────────────────────
def parse_skills(skill_str):
    skills = []
    if pd.isna(skill_str) or not str(skill_str).strip():
        return skills
    for p in str(skill_str).replace(",", ";").split(";"):
        p = p.strip()
        if not p:
            continue
        if ":" in p:
            skill, level = p.split(":", 1)
            try:
                skills.append((skill.strip(), int(level.strip())))
            except Exception:
                skills.append((skill.strip(), 1))
        else:
            skills.append((p, 1))
    return skills

# ─────────────────────────────────────────────
# Sidebar Filters
# ─────────────────────────────────────────────
st.sidebar.header("🔍 Filters")
dept_filter = st.sidebar.selectbox("Department", ["All"] + sorted(emp_df["Department"].dropna().unique()))
role_filter = st.sidebar.selectbox("Role",       ["All"] + sorted(emp_df["Role"].dropna().unique()))

filtered_df = emp_df.copy()
if dept_filter != "All": filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
if role_filter != "All": filtered_df = filtered_df[filtered_df["Role"]       == role_filter]

# ─────────────────────────────────────────────
# Build Skill DataFrame
# ─────────────────────────────────────────────
skill_rows = []
for _, row in filtered_df.iterrows():
    for skill, level in parse_skills(row["Skills"]):
        skill_rows.append({
            "Emp_ID":     row["Emp_ID"],
            "Name":       row["Name"],
            "Department": row["Department"],
            "Role":       row["Role"],
            "Skill":      skill,
            "Level":      level
        })

skill_df = pd.DataFrame(skill_rows)

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────
unique_skills  = skill_df["Skill"].nunique()  if not skill_df.empty else 0
avg_skill_lvl  = round(skill_df["Level"].mean(), 1) if not skill_df.empty else 0
top_skill      = skill_df["Skill"].value_counts().idxmax() if not skill_df.empty else "N/A"
emp_w_skills   = len(filtered_df)

k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Employees",         emp_w_skills)
k2.metric("🛠️ Unique Skills",     unique_skills)
k3.metric("📊 Avg Skill Level",   f"{avg_skill_lvl}/5")
k4.metric("🏆 Most Common Skill", top_skill)

st.divider()

# ─────────────────────────────────────────────
# Skill Inventory Table
# ─────────────────────────────────────────────
st.subheader("👩‍💼 Employee Skill Inventory")

tab1, tab2 = st.tabs(["📋 Skill Details", "👥 Employee View"])

with tab1:
    if not skill_df.empty:
        st.dataframe(skill_df, use_container_width=True, height=350)
        csv = skill_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export Skills CSV", csv, "skills_export.csv", "text/csv")
    else:
        st.info("No skill data for the current filter.")

with tab2:
    st.dataframe(
        filtered_df[["Emp_ID","Name","Department","Role","Skills"]],
        use_container_width=True, height=350
    )

st.divider()

# ─────────────────────────────────────────────
# Skill Analytics — Plotly
# ─────────────────────────────────────────────
st.subheader("📊 Skill Analytics")

skill_png = None

if not skill_df.empty:
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        avg_skill = skill_df.groupby("Skill")["Level"].mean().sort_values(ascending=False).head(20)
        fig1 = px.bar(
            avg_skill.reset_index().rename(columns={"Level":"Avg Level"}),
            x="Skill", y="Avg Level", text=avg_skill.values.round(1),
            title="Average Skill Level (Top 20)",
            color="Avg Level",
            color_continuous_scale="Blues",
            range_color=[1,5]
        )
        fig1.update_traces(textposition="outside",
                           hovertemplate="<b>%{x}</b><br>Avg Level: %{y:.1f}/5<extra></extra>")
        fig1.update_layout(
            xaxis_tickangle=-35,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=400, coloraxis_showscale=False
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_a2:
        # Skill count by department (heatmap-style)
        dept_skill = skill_df.groupby(["Department","Skill"]).size().reset_index(name="Count")
        top_skills = skill_df["Skill"].value_counts().head(10).index.tolist()
        dept_skill  = dept_skill[dept_skill["Skill"].isin(top_skills)]

        if not dept_skill.empty:
            pivot = dept_skill.pivot(index="Department", columns="Skill", values="Count").fillna(0)
            fig2 = px.imshow(pivot, title="Skill Presence by Department",
                             color_continuous_scale="Blues",
                             aspect="auto",
                             text_auto=True)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=400)
            st.plotly_chart(fig2, use_container_width=True)

    # Skill level distribution
    st.subheader("📈 Skill Level Distribution")
    level_counts = skill_df["Level"].value_counts().sort_index().reset_index()
    level_counts.columns = ["Level","Count"]
    level_counts["Label"] = "Level " + level_counts["Level"].astype(str)
    fig3 = px.bar(level_counts, x="Label", y="Count", text="Count",
                  title="Distribution of Skill Levels Across Workforce",
                  color="Level",
                  color_continuous_scale="Blues",
                  range_color=[1,5])
    fig3.update_traces(textposition="outside",
                       hovertemplate="<b>%{x}</b><br>%{y} skill entries<extra></extra>")
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=320, coloraxis_showscale=False
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Department-wise skill strength table
    st.subheader("🏢 Department-wise Skill Strength")
    dept_skill_avg = skill_df.groupby(["Department","Skill"])["Level"].mean().round(1).reset_index()
    dept_skill_avg.columns = ["Department","Skill","Avg Level"]
    st.dataframe(dept_skill_avg.sort_values(["Department","Avg Level"], ascending=[True,False]),
                 use_container_width=True, height=300)

    # PNG for PDF
    avg_skill_top = skill_df.groupby("Skill")["Level"].mean().sort_values(ascending=False).head(15)
    fig_m, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(avg_skill_top.index, avg_skill_top.values, color="#667eea")
    ax.set_title("Average Skill Level (Top 15)")
    ax.set_ylabel("Level (1–5)")
    ax.set_ylim(0, 5.5)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    for bar in bars:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig_m.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    skill_png = buf.read()
    plt.close(fig_m)
else:
    st.info("No skill data available for the current filter.")

st.divider()

# ─────────────────────────────────────────────
# Role Suggestion
# ─────────────────────────────────────────────
st.subheader("🔄 Role Suggestions Based on Skills")

emp_choice = st.selectbox(
    "Select Employee",
    (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist()
)
emp_id_sel = int(emp_choice.split(" — ")[0])
emp_row    = emp_df[emp_df["Emp_ID"] == emp_id_sel].iloc[0]
parsed     = parse_skills(emp_row["Skills"])

col_r1, col_r2 = st.columns(2)
col_r1.markdown(f"**Current Role:** {emp_row['Role']}")
col_r1.markdown(f"**Department:** {emp_row['Department']}")
col_r2.markdown(f"**Skills:** `{emp_row['Skills']}`")

ROLE_MAP = {
    "Software Developer":    ["Python","Java","JavaScript","React","Node.js"],
    "Data Analyst":          ["Python","SQL","Excel","Power BI","Analytics"],
    "DevOps Engineer":       ["Docker","Kubernetes","AWS","Linux","Git"],
    "HR Manager":            ["Communication","Recruitment","Leadership","Training"],
    "Finance Manager":       ["Excel","SAP","Financial Modelling","Accounting","GST"],
    "Sales Manager":         ["CRM","Negotiation","Lead Generation","Salesforce"],
    "Marketing Manager":     ["SEO","Google Ads","Content Writing","Analytics","HubSpot"],
    "Support Lead":          ["Communication","Zendesk","CRM","Customer Service"],
    "Operations Manager":    ["Excel","ERP","Supply Chain","Project Management"],
    "Legal Counsel":         ["Contract Law","Compliance","Legal Research","Drafting"],
}

skill_set = {s.lower() for s, _ in parsed if _ >= 3}
suggested = []
for r, req in ROLE_MAP.items():
    match = sum(1 for s in req if s.lower() in skill_set)
    if match >= 2:
        suggested.append((r, match))

suggested.sort(key=lambda x: x[1], reverse=True)

if suggested:
    st.success("💡 Suggested Roles: " + "  |  ".join(f"**{r}** ({m} skill matches)" for r, m in suggested[:4]))
else:
    st.info("No strong role matches found. Skill up to level 3+ in more areas.")

# ─────────────────────────────────────────────
# Update Role (Admin / HR)
# ─────────────────────────────────────────────
if role in ["Admin", "HR"]:
    st.divider()
    st.subheader("✏️ Update Employee Role")
    col_u1, col_u2 = st.columns(2)
    new_role    = col_u1.text_input("New Role",   placeholder="e.g. Senior Developer")
    new_skills  = col_u2.text_input("New Skills", value=emp_row["Skills"],
                                    placeholder="Python:4;SQL:3")

    if st.button("💾 Update Role & Skills"):
        updates = {}
        if new_role.strip():   updates["Role"]   = new_role.strip()
        if new_skills.strip(): updates["Skills"] = new_skills.strip()
        if updates:
            try:
                db.update_employee(emp_id_sel, updates)
                st.success("✅ Updated successfully.")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to update."); st.exception(e)
        else:
            st.warning("Enter a role or skills to update.")

# ─────────────────────────────────────────────
# PDF Export
# ─────────────────────────────────────────────
st.divider()
st.subheader("📄 Download Skills Report PDF")

if st.button("🖨️ Generate Skills PDF"):
    if skill_png is None:
        st.error("Please view the analytics first — graph needs to render.")
    else:
        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                projects_df=skill_df,
                project_fig=skill_png,
                title="Skill Inventory Report"
            )
            pdf_buffer.seek(0)
            st.download_button("⬇️ Download PDF", pdf_buffer, "skills_report.pdf", "application/pdf")
            st.success("✅ PDF ready!")
        except Exception as e:
            st.error("Failed to generate PDF."); st.exception(e)