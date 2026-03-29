# pages/7_Feedback.py
"""
Employee Feedback System — Workforce Intelligence System
- Consistent sidebar
- Plotly interactive analytics with hover
- Role-based edit/delete
- PDF export with graph
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import matplotlib.pyplot as plt

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.analytics import feedback_summary
from utils.pdf_export import generate_master_report

st.set_page_config(page_title="Feedback", page_icon="💬", layout="wide")
require_login()
show_role_badge()
logout_user()

role     = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "unknown")
user_data = db.get_user_by_username(username)
user_id   = user_data["id"] if user_data else None

st.title("💬 Employee Feedback System")

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────
try:
    emp_df = db.fetch_employees()
except Exception:
    emp_df = pd.DataFrame(columns=["Emp_ID","Name","Status"])

try:
    feedback_df = db.fetch_feedback()
except Exception:
    feedback_df = pd.DataFrame(columns=["feedback_id","sender_id","receiver_id","message","rating","log_date"])

# ─────────────────────────────────────────────
# Quick Stats
# ─────────────────────────────────────────────
if not feedback_df.empty:
    avg_r    = round(feedback_df["rating"].mean(), 2)
    total_fb = len(feedback_df)
    excellent = len(feedback_df[feedback_df["rating"] >= 4])
    poor_fb   = len(feedback_df[feedback_df["rating"] <= 2])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💬 Total Feedback",   total_fb)
    k2.metric("⭐ Avg Rating",        f"{avg_r}/5")
    k3.metric("🌟 Excellent (4-5★)",  excellent)
    k4.metric("⚠️ Poor (1-2★)",       poor_fb)
    st.divider()

# ─────────────────────────────────────────────
# Submit Feedback
# ─────────────────────────────────────────────
st.subheader("➕ Submit Feedback")

with st.form("add_feedback_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    receiver_options = (emp_df["Emp_ID"].astype(str) + " — " + emp_df["Name"]).tolist() if not emp_df.empty else []
    receiver = col1.selectbox("Select Employee to Give Feedback", receiver_options)
    rating   = col2.slider("⭐ Rating (1 = Poor, 5 = Excellent)", 1, 5, 3)

    # Visual star display
    stars = "⭐" * rating + "☆" * (5 - rating)
    col2.markdown(f"**{stars}**")

    message = st.text_area("Feedback Message *", height=100,
                            placeholder="Be specific and constructive...")
    submit  = st.form_submit_button("📨 Submit Feedback", use_container_width=True, type="primary")

    if submit:
        if not receiver or not message.strip():
            st.error("Please select an employee and write your feedback.")
        else:
            receiver_id = int(receiver.split(" — ")[0])
            try:
                db.add_feedback(user_id, receiver_id, message.strip(), rating)
                st.success("✅ Feedback submitted successfully.")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to submit feedback.")
                st.exception(e)

st.divider()

# ─────────────────────────────────────────────
# View Feedback Records
# ─────────────────────────────────────────────
st.subheader("📋 Feedback Records")

if not feedback_df.empty and not emp_df.empty:
    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
    feedback_df = feedback_df.copy()
    feedback_df["Sender"]   = feedback_df["sender_id"].map(emp_map).fillna("Anonymous")
    feedback_df["Receiver"] = feedback_df["receiver_id"].map(emp_map).fillna("Unknown")
    feedback_df["Stars"]    = feedback_df["rating"].apply(lambda r: "⭐" * int(r) if pd.notna(r) else "")

    # Filters
    col_f1, col_f2 = st.columns(2)
    f_receiver = col_f1.selectbox("Filter by Receiver", ["All"] + sorted(feedback_df["Receiver"].unique().tolist()))
    f_rating   = col_f2.selectbox("Filter by Rating",   ["All","5 ⭐","4 ⭐","3 ⭐","2 ⭐","1 ⭐"])

    fb_display = feedback_df.copy()
    if f_receiver != "All":
        fb_display = fb_display[fb_display["Receiver"] == f_receiver]
    if f_rating != "All":
        r_val = int(f_rating[0])
        fb_display = fb_display[fb_display["rating"] == r_val]

    st.dataframe(
        fb_display[["feedback_id","Sender","Receiver","message","Stars","log_date"]].rename(
            columns={"feedback_id":"ID","message":"Message","log_date":"Date","Stars":"Rating"}
        ),
        height=300, use_container_width=True
    )
else:
    st.info("No feedback records yet.")

st.divider()

# ─────────────────────────────────────────────
# Edit / Delete Feedback
# ─────────────────────────────────────────────
st.subheader("✏️ Edit / Delete Feedback")

editable_df = feedback_df.copy() if not feedback_df.empty else pd.DataFrame()

if not editable_df.empty:
    if role != "Admin" and user_id:
        editable_df = editable_df[editable_df["sender_id"] == user_id]

if editable_df.empty:
    st.info("No feedback available for editing.")
else:
    fb_options = editable_df["feedback_id"].astype(str) + " — " + editable_df["Receiver"] + " (" + editable_df["rating"].astype(str) + "★)"
    sel_id_str = st.selectbox("Select Feedback to Edit/Delete", fb_options.tolist())
    sel_id     = int(sel_id_str.split(" — ")[0])
    row        = editable_df[editable_df["feedback_id"] == sel_id].iloc[0]

    with st.form("edit_feedback_form"):
        col_e1, col_e2 = st.columns(2)
        new_msg    = col_e1.text_area("Message", value=row["message"], height=100)
        new_rating = col_e2.slider("Rating", 1, 5, int(row["rating"]))
        col_e2.markdown("⭐" * new_rating + "☆" * (5 - new_rating))

        col_u, col_d = st.columns(2)
        update_btn = col_u.form_submit_button("💾 Update",  use_container_width=True)
        delete_btn = col_d.form_submit_button("🗑️ Delete", use_container_width=True)

        if update_btn:
            try:
                db.update_feedback(sel_id, new_msg.strip(), new_rating)
                st.success("✅ Feedback updated.")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to update."); st.exception(e)

        if delete_btn:
            try:
                db.delete_feedback(sel_id)
                st.success("🗑️ Feedback deleted.")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to delete."); st.exception(e)

st.divider()

# ─────────────────────────────────────────────
# Feedback Analytics — Plotly
# ─────────────────────────────────────────────
st.subheader("📊 Feedback Analytics")

feedback_png = None

if not feedback_df.empty and not emp_df.empty:
    summary_df = feedback_summary(feedback_df, emp_df)

    if not summary_df.empty:
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            fig1 = px.bar(
                summary_df.sort_values("Avg_Rating"),
                x="Avg_Rating", y="Employee", orientation="h",
                text=summary_df.sort_values("Avg_Rating")["Avg_Rating"].round(1),
                title="Average Feedback Rating per Employee",
                color="Avg_Rating",
                color_continuous_scale=["#ef4444","#f59e0b","#22c55e"],
                range_color=[1,5],
                hover_data={"Feedback_Count":True}
            )
            fig1.update_traces(textposition="outside")
            fig1.update_layout(
                xaxis=dict(range=[0,5.5]), yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=max(320, len(summary_df)*30),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col_a2:
            # Rating distribution
            r_dist = feedback_df["rating"].value_counts().sort_index().reset_index()
            r_dist.columns = ["Rating","Count"]
            r_dist["Label"] = r_dist["Rating"].astype(str) + " ⭐"
            fig2 = px.bar(r_dist, x="Label", y="Count", text="Count",
                          title="Rating Distribution",
                          color="Rating",
                          color_continuous_scale=["#ef4444","#f59e0b","#22c55e"],
                          range_color=[1,5])
            fig2.update_traces(textposition="outside")
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=320, coloraxis_showscale=False, showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(summary_df.sort_values("Avg_Rating", ascending=False), use_container_width=True)

        # Matplotlib PNG for PDF
        fig_m, ax = plt.subplots(figsize=(8, 4))
        bars = ax.bar(summary_df["Employee"], summary_df["Avg_Rating"], color="#667eea")
        ax.set_ylabel("Avg Rating"); ax.set_title("Average Feedback Rating per Employee")
        ax.set_ylim(0, 5.5)
        plt.xticks(rotation=45, ha="right", fontsize=8)
        for bar in bars:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                    f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8)
        plt.tight_layout()
        buf = io.BytesIO()
        fig_m.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        feedback_png = buf.read()
        plt.close(fig_m)

# ─────────────────────────────────────────────
# PDF Export
# ─────────────────────────────────────────────
st.divider()
st.subheader("📄 Export Feedback Report")

if st.button("🖨️ Generate Feedback PDF"):
    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=emp_df,
            notifications_df=feedback_df[["feedback_id","Sender","Receiver","message","rating","log_date"]].rename(
                columns={"feedback_id":"id"}
            ) if not feedback_df.empty else pd.DataFrame(),
            notification_fig=feedback_png,
            title="Employee Feedback Report"
        )
        pdf_buffer.seek(0)
        st.download_button("⬇️ Download PDF", pdf_buffer, "feedback_report.pdf", "application/pdf")
        st.success("✅ PDF ready!")
    except Exception as e:
        st.error("Failed to generate PDF."); st.exception(e)