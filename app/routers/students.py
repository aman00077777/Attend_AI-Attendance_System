"""
routers/students.py — FastAPI router for student management.

Endpoints:
  POST /api/students/register  — Register a new student with face photo
  GET  /api/students           — List all students
  GET  /api/students/{id}      — Get a single student
  DELETE /api/students/{id}    — Remove a student (and cascades attendance)
"""

from __future__ import annotations

import base64
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger

from app.config import get_settings
from app.database import get_supabase_admin
from app.models.schemas import MessageResponse, StudentOut
from app.services.face_service import extract_embedding

router = APIRouter(prefix="/api/students", tags=["students"])
settings = get_settings()


# ─── Register ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_student(
    name: str = Form(...),
    roll_number: str = Form(...),
    branch: str = Form(...),
    year: int = Form(...),
    photo: UploadFile = File(..., description="Student face photo (JPEG/PNG)"),
    db=Depends(get_supabase_admin),
):
    """Register a new student: extract face embedding and store in Supabase."""
    roll_number = roll_number.strip().upper()
    logger.info("Registering student: {} ({})", name, roll_number)

    # ── Check for duplicate roll number ────────────────────────────────────────
    existing = (
        db.table("students")
        .select("id")
        .eq("roll_number", roll_number)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Roll number '{roll_number}' is already registered.",
        )

    # ── Read photo bytes and encode as base64 ──────────────────────────────────
    photo_bytes = await photo.read()
    if not photo_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty photo file."
        )
    photo_b64 = base64.b64encode(photo_bytes).decode("utf-8")

    # ── Extract face embedding ─────────────────────────────────────────────────
    try:
        embedding = extract_embedding(photo_b64)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    # ── Upload photo to Supabase storage (bucket: student-photos) ─────────────
    student_id = str(uuid.uuid4())
    photo_filename = f"{student_id}.jpg"
    photo_url: str | None = None
    try:
        db.storage.from_("student-photos").upload(
            path=photo_filename,
            file=photo_bytes,
            file_options={"content-type": photo.content_type or "image/jpeg"},
        )
        supabase_cfg = settings.supabase_url
        photo_url = (
            f"{supabase_cfg}/storage/v1/object/public/student-photos/{photo_filename}"
        )
        logger.info("Photo uploaded → {}", photo_url)
    except Exception as exc:
        logger.warning("Photo upload failed (non-fatal): {}", exc)
        # Continue without photo URL — face encoding is the critical part

    # ── Insert into students table ─────────────────────────────────────────────
    payload = {
        "id": student_id,
        "name": name.strip(),
        "roll_number": roll_number,
        "branch": branch.strip(),
        "year": year,
        "face_encoding": embedding,
        "photo_url": photo_url,
    }
    result = db.table("students").insert(payload).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database insert failed.",
        )

    logger.success("Student registered: {} id={}", name, student_id)
    return MessageResponse(
        message=f"Student '{name}' registered successfully.",
        data={"id": student_id, "roll_number": roll_number},
    )


# ─── List all students ────────────────────────────────────────────────────────

@router.get("/", response_model=List[StudentOut])
def list_students(db=Depends(get_supabase_admin)):
    result = (
        db.table("students")
        .select("id, name, roll_number, branch, year, photo_url, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ─── Get one student ──────────────────────────────────────────────────────────

@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: str, db=Depends(get_supabase_admin)):
    result = (
        db.table("students")
        .select("id, name, roll_number, branch, year, photo_url, created_at")
        .eq("id", student_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Student not found.")
    return result.data


# ─── Delete a student ─────────────────────────────────────────────────────────

@router.delete("/{student_id}", response_model=MessageResponse)
def delete_student(student_id: str, db=Depends(get_supabase_admin)):
    result = db.table("students").delete().eq("id", student_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Student not found.")
    logger.info("Deleted student id={}", student_id)
    return MessageResponse(message="Student deleted.", data={"id": student_id})
