"""dashboard/routes/reports.py — Attendance reports + PDF/CSV export."""

import io
import os
from datetime import date, datetime

import requests
from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from loguru import logger
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

reports_bp = Blueprint("reports", __name__)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def _fetch_report(start_date=None, end_date=None, subject=None, student_id=None):
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if subject:
        params["subject"] = subject
    if student_id:
        params["student_id"] = student_id
    try:
        resp = requests.get(f"{API_BASE}/api/attendance/report", params=params, timeout=15)
        return resp.json() if resp.ok else {}
    except Exception as exc:
        logger.warning("Report fetch error: {}", exc)
        return {}


def _fetch_students():
    try:
        resp = requests.get(f"{API_BASE}/api/students/", timeout=10)
        return resp.json() if resp.ok else []
    except Exception:
        return []


@reports_bp.route("/reports")
def reports_page():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    subject = request.args.get("subject", "")
    student_id = request.args.get("student_id", "")

    data = _fetch_report(start_date, end_date, subject, student_id)
    records = data.get("records", [])
    students = _fetch_students()

    # Build per-student stats from records
    stats_map = {}
    for r in records:
        sid = r["student_id"]
        if sid not in stats_map:
            stats_map[sid] = {
                "name": r["student_name"],
                "roll_number": r["roll_number"],
                "branch": r["branch"],
                "total": 0,
                "present": 0,
            }
        stats_map[sid]["total"] += 1
        if r["status"] == "present":
            stats_map[sid]["present"] += 1

    for s in stats_map.values():
        s["percent"] = round(s["present"] / s["total"] * 100, 1) if s["total"] else 0

    stats = sorted(stats_map.values(), key=lambda x: x["percent"])

    # Chart data
    date_counts: dict[str, int] = {}
    for r in records:
        d = r.get("date", "")
        if r.get("status") == "present":
            date_counts[d] = date_counts.get(d, 0) + 1
    sorted_dates = sorted(date_counts.keys())
    chart_labels = sorted_dates
    chart_values = [date_counts[d] for d in sorted_dates]

    return render_template(
        "reports.html",
        records=records,
        stats=stats,
        students=students,
        chart_labels=chart_labels,
        chart_values=chart_values,
        filters={"start_date": start_date, "end_date": end_date, "subject": subject, "student_id": student_id},
        total=len(records),
    )


@reports_bp.route("/reports/export/pdf")
def export_pdf():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    subject = request.args.get("subject", "")
    student_id = request.args.get("student_id", "")

    data = _fetch_report(start_date, end_date, subject, student_id)
    records = data.get("records", [])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#6C63FF"),
        spaceAfter=10,
    )
    sub_style = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#888888"),
        spaceAfter=20,
    )

    elements = []
    elements.append(Paragraph("Attendance Report", title_style))
    elements.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"Records: {len(records)}"
            + (f" | Subject: {subject}" if subject else ""),
            sub_style,
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    # Table
    header = ["#", "Name", "Roll No.", "Branch", "Year", "Subject", "Date", "Time", "Status"]
    table_data = [header]
    for i, r in enumerate(records, start=1):
        status_text = "[P] Present" if r.get("status") == "present" else "[A] Absent"
        table_data.append([
            str(i),
            r.get("student_name", ""),
            r.get("roll_number", ""),
            r.get("branch", ""),
            str(r.get("year", "")),
            r.get("subject", ""),
            r.get("date", ""),
            r.get("time", "")[:8] if r.get("time") else "",
            status_text,
        ])

    col_widths = [1 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm, 1.2 * cm, 2.5 * cm, 2.2 * cm, 1.8 * cm, 2.3 * cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6C63FF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8F9FA"), colors.white]),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("ROWHEIGHT", (0, 0), (-1, -1), 20),
        ])
    )
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)

    filename = f"attendance_report_{date.today()}.pdf"
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/reports/export/csv")
def export_csv():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    subject = request.args.get("subject", "")

    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if subject:
        params["subject"] = subject

    try:
        resp = requests.get(
            f"{API_BASE}/api/attendance/export/csv", params=params, timeout=30
        )
        filename = f"attendance_{date.today()}.csv"
        return Response(
            resp.content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        flash(f"CSV export failed: {exc}", "danger")
        return redirect(url_for("reports.reports_page"))
