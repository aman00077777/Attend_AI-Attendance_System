"""
routers/attendance.py — FastAPI router for attendance management.

Endpoints:
  POST /api/attendance/mark          — Mark attendance via face recognition
  GET  /api/attendance/today         — Today's attendance records
  GET  /api/attendance/report        — Filtered report (date range, student, subject)
  GET  /api/attendance/stats         — Attendance % per student
  GET  /api/attendance/trend         — 30-day daily counts for charts
  GET  /api/attendance/export/csv    — CSV download
"""

from __future__ import annotations

import asyncio
import csv
import io
import uuid
from datetime import date, datetime
from functools import partial

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger

from app.database import get_supabase_admin
from app.models.schemas import (
    AttendanceMarkRequest,
    MessageResponse,
)
from app.services.face_service import extract_embedding, find_best_match

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


# ─── Mark attendance ──────────────────────────────────────────────────────────

@router.post("/mark", response_model=MessageResponse)
async def mark_attendance(
    payload: AttendanceMarkRequest,
    db=Depends(get_supabase_admin),
):
    """
    Accept a Base-64 webcam frame, identify the student via face matching,
    and insert an attendance record (subject-level deduplication enforced).
    """
    target_date = payload.date or date.today()
    subject = payload.subject.strip()

    logger.info("Attendance mark request: subject={} date={}", subject, target_date)

    # ── Extract probe embedding (blocking — run in thread pool) ────────────────────
    loop = asyncio.get_running_loop()
    try:
        probe = await loop.run_in_executor(
            None, partial(extract_embedding, payload.image_b64)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    # ── Load all student embeddings ────────────────────────────────────────────
    students_result = (
        db.table("students")
        .select("id, name, roll_number, branch, year, face_encoding")
        .execute()
    )
    students = students_result.data or []
    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No students registered yet.",
        )

    # ── Find best match ────────────────────────────────────────────────────────
    matched = find_best_match(probe, students)
    if matched is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face not recognised. Please register first or try again.",
        )

    student_id = str(matched["id"])
    student_name = matched["name"]
    roll_number = matched["roll_number"]

    # ── Check for duplicate attendance ────────────────────────────────────────
    dup_check = (
        db.table("attendance")
        .select("id")
        .eq("student_id", student_id)
        .eq("date", str(target_date))
        .eq("subject", subject)
        .execute()
    )
    if dup_check.data:
        logger.warning(
            "Duplicate attendance attempt: {} subject={} date={}",
            roll_number, subject, target_date,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attendance for '{student_name}' in '{subject}' already marked for {target_date}.",
        )

    # ── Insert attendance record ───────────────────────────────────────────────
    now = datetime.now()
    record = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "date": str(target_date),
        "time": now.strftime("%H:%M:%S"),
        "subject": subject,
        "status": "present",
    }
    insert_result = db.table("attendance").insert(record).execute()
    if not insert_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save attendance record.",
        )

    logger.success(
        "Attendance marked: {} ({}) subject={} date={}",
        student_name, roll_number, subject, target_date,
    )
    return MessageResponse(
        message=f"Attendance marked for {student_name}.",
        data={
            "student_name": student_name,
            "roll_number": roll_number,
            "subject": subject,
            "date": str(target_date),
            "time": now.strftime("%H:%M:%S"),
            "distance": round(matched.get("_distance", 0), 4),
        },
    )


# ─── Today's attendance ───────────────────────────────────────────────────────

@router.get("/today")
def today_attendance(db=Depends(get_supabase_admin)):
    today = str(date.today())
    result = (
        db.table("attendance")
        .select("*, students(name, roll_number, branch, year)")
        .eq("date", today)
        .order("time", desc=False)
        .execute()
    )
    records = []
    for row in (result.data or []):
        student = row.get("students") or {}
        records.append({
            "id": row["id"],
            "student_id": row["student_id"],
            "student_name": student.get("name", "—"),
            "roll_number": student.get("roll_number", "—"),
            "branch": student.get("branch", "—"),
            "year": student.get("year"),
            "subject": row["subject"],
            "time": row["time"],
            "status": row["status"],
            "date": row["date"],
        })
    return {"date": today, "count": len(records), "records": records}


# ─── Filtered report ──────────────────────────────────────────────────────────

@router.get("/report")
def attendance_report(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    student_id: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    db=Depends(get_supabase_admin),
):
    query = (
        db.table("attendance")
        .select("*, students(name, roll_number, branch, year)")
        .order("date", desc=True)
    )
    if start_date:
        query = query.gte("date", start_date)
    if end_date:
        query = query.lte("date", end_date)
    if student_id:
        query = query.eq("student_id", student_id)
    if subject:
        query = query.eq("subject", subject)

    result = query.execute()
    records = []
    for row in (result.data or []):
        student = row.get("students") or {}
        records.append({
            "id": row["id"],
            "student_id": row["student_id"],
            "student_name": student.get("name", "—"),
            "roll_number": student.get("roll_number", "—"),
            "branch": student.get("branch", "—"),
            "year": student.get("year"),
            "subject": row["subject"],
            "time": row["time"],
            "status": row["status"],
            "date": row["date"],
            "created_at": row.get("created_at"),
        })
    return {"count": len(records), "records": records}


# ─── Attendance stats (% per student) ────────────────────────────────────────

@router.get("/stats")
def attendance_stats(db=Depends(get_supabase_admin)):
    result = db.table("vw_attendance_percentage").select("*").execute()
    return {"stats": result.data or []}


# ─── 30-day trend ─────────────────────────────────────────────────────────────

@router.get("/trend")
def attendance_trend(db=Depends(get_supabase_admin)):
    result = (
        db.table("vw_30day_trend")
        .select("date, present_count")
        .order("date")
        .execute()
    )
    return {"trend": result.data or []}


# ─── CSV export ───────────────────────────────────────────────────────────────

@router.get("/export/csv")
def export_csv(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    db=Depends(get_supabase_admin),
):
    query = (
        db.table("attendance")
        .select("*, students(name, roll_number, branch, year)")
        .order("date", desc=True)
    )
    if start_date:
        query = query.gte("date", start_date)
    if end_date:
        query = query.lte("date", end_date)
    if subject:
        query = query.eq("subject", subject)

    result = query.execute()
    rows = result.data or []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Roll Number", "Branch", "Year", "Subject", "Date", "Time", "Status"])
    for row in rows:
        s = row.get("students") or {}
        writer.writerow([
            s.get("name", ""),
            s.get("roll_number", ""),
            s.get("branch", ""),
            s.get("year", ""),
            row.get("subject", ""),
            row.get("date", ""),
            row.get("time", ""),
            row.get("status", ""),
        ])

    output.seek(0)
    filename = f"attendance_{date.today()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
