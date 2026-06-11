"""dashboard/routes/students.py — Student management routes."""

import os

import requests
from flask import Blueprint, flash, redirect, render_template, request, url_for
from loguru import logger

students_bp = Blueprint("students", __name__)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8001")


@students_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


@students_bp.route("/register", methods=["POST"])
def register_submit():
    name = request.form.get("name", "").strip()
    roll_number = request.form.get("roll_number", "").strip()
    branch = request.form.get("branch", "").strip()
    year = request.form.get("year", "").strip()
    photo_file = request.files.get("photo")

    # Validation
    if not all([name, roll_number, branch, year]):
        flash("All fields are required.", "danger")
        return redirect(url_for("students.register_page"))

    if not photo_file or photo_file.filename == "":
        flash("Please upload or capture a photo.", "danger")
        return redirect(url_for("students.register_page"))

    try:
        # Seek to start in case Flask already read the stream internally
        photo_file.stream.seek(0)
        resp = requests.post(
            f"{API_BASE}/api/students/register",
            data={"name": name, "roll_number": roll_number, "branch": branch, "year": year},
            files={"photo": (photo_file.filename, photo_file.stream, photo_file.content_type or "image/jpeg")},
            timeout=120,  # face encoding takes time
        )
        data = resp.json()
        if resp.status_code == 201:
            flash(f"✅ {data.get('message', 'Student registered!')}", "success")
            return redirect(url_for("home.index"))
        else:
            flash(f"❌ {data.get('detail', 'Registration failed.')}", "danger")
    except requests.exceptions.ConnectionError:
        flash("❌ Cannot connect to the API. Is the backend running?", "danger")
    except Exception as exc:
        logger.exception("Registration error: {}", exc)
        flash(f"❌ Unexpected error: {exc}", "danger")

    return redirect(url_for("students.register_page"))


@students_bp.route("/students")
def students_list():
    try:
        resp = requests.get(f"{API_BASE}/api/students/", timeout=10)
        students = resp.json() if resp.ok else []
    except Exception:
        students = []
    return render_template("students_list.html", students=students)


@students_bp.route("/students/<student_id>/delete", methods=["POST"])
def delete_student(student_id: str):
    try:
        resp = requests.delete(f"{API_BASE}/api/students/{student_id}", timeout=10)
        if resp.ok:
            flash("Student deleted.", "success")
        else:
            flash("Failed to delete student.", "danger")
    except Exception as exc:
        flash(f"Error: {exc}", "danger")
    return redirect(url_for("students.students_list"))
