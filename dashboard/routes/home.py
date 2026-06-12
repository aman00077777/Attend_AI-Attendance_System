"""dashboard/routes/home.py — Admin dashboard home page."""

import os
from datetime import date

import requests
from flask import Blueprint, render_template
from loguru import logger

home_bp = Blueprint("home", __name__)

# 👇 Yahan localhost ki jagah Hugging Face ka URL daal diya hai
API_BASE = os.getenv("API_BASE_URL", "https://aman20061203-attend-ai-backend.hf.space")


def _safe_get(url: str, default=None):
    try:
        # 👇 Timeout 10 se badha kar 30 seconds kar diya hai
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("API call failed {}: {}", url, exc)
        return default


@home_bp.route("/")
def index():
    # ── Total students ─────────────────────────────────────────────────────────
    students_data = _safe_get(f"{API_BASE}/api/students/", default=[])
    total_students = len(students_data) if isinstance(students_data, list) else 0

    # ── Today's attendance ────────────────────────────────────────────────────
    today_data = _safe_get(f"{API_BASE}/api/attendance/today", default={})
    today_count = today_data.get("count", 0) if today_data else 0

    # ── Attendance stats for low-attendance alert ──────────────────────────────
    stats_data = _safe_get(f"{API_BASE}/api/attendance/stats", default={})
    all_stats = stats_data.get("stats", []) if stats_data else []

    low_attendance = [
        s for s in all_stats
        if s.get("total_classes", 0) > 0
        and float(s.get("attendance_percent", 100)) < 75
    ]

    # ── 30-day trend for Chart.js ─────────────────────────────────────────────
    trend_data = _safe_get(f"{API_BASE}/api/attendance/trend", default={})
    trend = trend_data.get("trend", []) if trend_data else []
    trend_labels = [t["date"] for t in trend]
    trend_values = [t["present_count"] for t in trend]

    # ── Recent attendance records ─────────────────────────────────────────────
    today_records = today_data.get("records", []) if today_data else []

    return render_template(
        "index.html",
        total_students=total_students,
        today_count=today_count,
        low_attendance=low_attendance,
        trend_labels=trend_labels,
        trend_values=trend_values,
        today_records=today_records[:10],
        today=str(date.today()),
    )