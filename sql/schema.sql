-- ============================================================
-- Face Recognition Attendance System — Supabase Schema
-- Run this in your Supabase SQL editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── students ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id            UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          TEXT         NOT NULL,
    roll_number   TEXT         NOT NULL UNIQUE,
    branch        TEXT         NOT NULL,
    year          INTEGER      NOT NULL CHECK (year BETWEEN 1 AND 4),
    face_encoding JSONB,
    photo_url     TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Index for fast lookup by roll number
CREATE INDEX IF NOT EXISTS idx_students_roll_number ON students(roll_number);

-- ─── attendance ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id  UUID        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    date        DATE        NOT NULL DEFAULT CURRENT_DATE,
    time        TIME        NOT NULL DEFAULT CURRENT_TIME,
    subject     TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'present' CHECK (status IN ('present', 'absent')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate attendance for same student/date/subject
    CONSTRAINT uq_attendance_student_date_subject UNIQUE (student_id, date, subject)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_attendance_date        ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_attendance_student_id  ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_subject     ON attendance(subject);

-- ─── Row Level Security (optional — enable if you use Supabase auth) ──────────
-- ALTER TABLE students  ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- ─── Helpful Views ────────────────────────────────────────────────────────────

-- Today's attendance with student details
CREATE OR REPLACE VIEW vw_today_attendance AS
SELECT
    a.id,
    s.name,
    s.roll_number,
    s.branch,
    s.year,
    a.subject,
    a.time,
    a.status,
    a.date
FROM attendance a
JOIN students s ON s.id = a.student_id
WHERE a.date = CURRENT_DATE;

-- Attendance percentage per student
CREATE OR REPLACE VIEW vw_attendance_percentage AS
SELECT
    s.id,
    s.name,
    s.roll_number,
    s.branch,
    s.year,
    COUNT(a.id)                                                   AS total_classes,
    COUNT(a.id) FILTER (WHERE a.status = 'present')               AS present_count,
    ROUND(
        COUNT(a.id) FILTER (WHERE a.status = 'present') * 100.0
        / NULLIF(COUNT(a.id), 0),
        2
    )                                                              AS attendance_percent
FROM students s
LEFT JOIN attendance a ON a.student_id = s.id
GROUP BY s.id, s.name, s.roll_number, s.branch, s.year;

-- 30-day trend (daily present count)
CREATE OR REPLACE VIEW vw_30day_trend AS
SELECT
    date,
    COUNT(*) FILTER (WHERE status = 'present') AS present_count
FROM attendance
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date;
