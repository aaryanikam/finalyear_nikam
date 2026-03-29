"""
PDF Export Utilities — Workforce Intelligence System (FINAL FIXED)
- Auto-fit tables
- Wrap long text
- Prevent cut-off
- Supports charts (PNG bytes)
- Table + Graph per section
- Dashboard / Attendance / Mood / Projects / Notifications graphs supported
"""

import io
import re
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


# --------------------------
# SANITIZE TEXT
# --------------------------
def _sanitize(value):
    if value is None:
        return ""
    text = str(value)
    text = text.replace("😊", "Happy").replace("😐", "Neutral")
    text = text.replace("😔", "Sad").replace("😡", "Angry")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()


# --------------------------
# BUILD SAFE TABLE
# --------------------------
def _build_table(df, page_width):
    if df is None or df.empty:
        return None

    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(_sanitize)

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "cell",
        parent=styles["Normal"],
        fontSize=7,
        leading=9
    )

    data = [list(df.columns)]
    for _, row in df.iterrows():
        data.append([Paragraph(str(cell), cell_style) for cell in row])

    col_count = len(df.columns)
    col_width = page_width / col_count
    col_widths = [col_width] * col_count

    table = Table(data, colWidths=col_widths, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return table


# --------------------------
# PNG → IMAGE
# --------------------------
def _png_to_image(png_bytes, width=9, height=4):
    if png_bytes is None:
        return None
    try:
        buf = io.BytesIO(png_bytes)
        return Image(buf, width * inch, height * inch)
    except Exception:
        return None


# --------------------------
# MASTER REPORT
# --------------------------
def generate_master_report(
    buffer,
    employees_df=None,
    attendance_df=None,
    mood_df=None,
    projects_df=None,
    notifications_df=None,
    dashboard_fig=None,
    attendance_fig=None,
    mood_fig=None,
    project_fig=None,
    notification_fig=None,
    title="MASTER WORKFORCE REPORT"
):
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    elements = []
    page_width = doc.width

    title_style = ParagraphStyle(
        "title",
        fontSize=18,
        alignment=1,
        spaceAfter=20
    )

    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))

    # ---------------- DASHBOARD
    if dashboard_fig:
        elements.append(Paragraph("Dashboard Analytics", styles["Heading2"]))
        img = _png_to_image(dashboard_fig)
        if img:
            elements.append(Spacer(1, 12))
            elements.append(img)
        elements.append(PageBreak())

    # ---------------- EMPLOYEES
    if employees_df is not None and not employees_df.empty:
        elements.append(Paragraph("Employees", styles["Heading2"]))
        table = _build_table(employees_df, page_width)
        if table:
            elements.append(table)
        elements.append(PageBreak())

    # ---------------- ATTENDANCE
    if attendance_df is not None and not attendance_df.empty:
        elements.append(Paragraph("Attendance", styles["Heading2"]))
        table = _build_table(attendance_df, page_width)
        if table:
            elements.append(table)
        if attendance_fig:
            img = _png_to_image(attendance_fig)
            if img:
                elements.append(Spacer(1, 12))
                elements.append(img)
        elements.append(PageBreak())

    # ---------------- MOOD
    if mood_df is not None and not mood_df.empty:
        elements.append(Paragraph("Mood Analytics", styles["Heading2"]))
        table = _build_table(mood_df, page_width)
        if table:
            elements.append(table)
        if mood_fig:
            img = _png_to_image(mood_fig)
            if img:
                elements.append(Spacer(1, 12))
                elements.append(img)
        elements.append(PageBreak())

    # ---------------- PROJECTS
    if projects_df is not None and not projects_df.empty:
        elements.append(Paragraph("Projects", styles["Heading2"]))
        table = _build_table(projects_df, page_width)
        if table:
            elements.append(table)
        if project_fig:
            img = _png_to_image(project_fig)
            if img:
                elements.append(Spacer(1, 12))
                elements.append(img)
        elements.append(PageBreak())

    # ---------------- NOTIFICATIONS
    if notifications_df is not None and not notifications_df.empty:
        elements.append(Paragraph("Notifications", styles["Heading2"]))
        table = _build_table(notifications_df, page_width)
        if table:
            elements.append(table)
        if notification_fig:
            img = _png_to_image(notification_fig)
            if img:
                elements.append(Spacer(1, 12))
                elements.append(img)
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)


# --------------------------
# SUMMARY PDF
# --------------------------
def generate_summary_pdf(buffer, total=0, active=0, resigned=0, df=None, title="Summary Report"):
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Records: {total}", styles["Normal"]))
    elements.append(Paragraph(f"Active: {active}", styles["Normal"]))
    elements.append(Paragraph(f"Closed / Resigned: {resigned}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    if df is not None and not df.empty:
        table = _build_table(df, doc.width)
        if table:
            elements.append(table)

    doc.build(elements)
    buffer.seek(0)
