"""
schemas.py — Pydantic request/response models for the FastAPI backend.
"""

from __future__ import annotations

from datetime import date, time, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─── Student ──────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    roll_number: str = Field(..., min_length=1, max_length=30)
    branch: str = Field(..., min_length=1, max_length=60)
    year: int = Field(..., ge=1, le=4)

    @field_validator("roll_number")
    @classmethod
    def normalise_roll(cls, v: str) -> str:
        return v.strip().upper()


class StudentOut(BaseModel):
    id: UUID
    name: str
    roll_number: str
    branch: str
    year: int
    photo_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StudentWithEncoding(StudentOut):
    face_encoding: Optional[List[float]] = None


# ─── Attendance ───────────────────────────────────────────────────────────────

class AttendanceMarkRequest(BaseModel):
    """Sent by the dashboard when a face is captured."""
    image_b64: str = Field(..., description="Base-64 encoded JPEG/PNG frame")
    subject: str = Field(..., min_length=1, max_length=100)
    date: Optional[date] = None   # defaults to today on the server


class AttendanceOut(BaseModel):
    id: UUID
    student_id: UUID
    student_name: str
    roll_number: str
    date: date
    time: time
    subject: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceReportFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    student_id: Optional[UUID] = None
    subject: Optional[str] = None


class AttendanceStats(BaseModel):
    student_id: UUID
    name: str
    roll_number: str
    branch: str
    year: int
    total_classes: int
    present_count: int
    attendance_percent: float


# ─── Generic responses ────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    detail: str
