"""dashboard/routes/attendance.py — Attendance marking routes."""

import os

import requests
from flask import Blueprint, jsonify, render_template, request
from loguru import logger

attendance_bp = Blueprint("attendance", __name__)

# 👇 Yahan localhost ki jagah Hugging Face ka URL daal diya hai
API_BASE = os.getenv("API_BASE_URL", "https://aman20061203-attend-ai-backend.hf.space")


@attendance_bp.route("/attendance", methods=["GET"])
def attendance_page():
    return render_template("attendance.html")


@attendance_bp.route("/attendance/mark", methods=["POST"])
def mark_attendance():
    """
    Receive base64 image + subject from the JS webcam capture,
    forward to FastAPI, return JSON result.
    """
    data = request.get_json(force=True, silent=True) or {}
    image_b64 = data.get("image_b64", "")
    subject = data.get("subject", "").strip()

    if not image_b64:
        return jsonify({"success": False, "message": "No image data received."}), 400
    if not subject:
        return jsonify({"success": False, "message": "Subject is required."}), 400

    try:
        resp = requests.post(
            f"{API_BASE}/api/attendance/mark",
            json={"image_b64": image_b64, "subject": subject},
            timeout=120,  # 👇 Timeout badha kar 120 seconds kar diya hai
        )
        result = resp.json()
        if resp.status_code == 200:
            return jsonify({"success": True, "message": result.get("message", "Marked!"), "data": result.get("data", {})})
        else:
            return jsonify({"success": False, "message": result.get("detail", "Failed.")}), resp.status_code
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to FastAPI backend")
        return jsonify({"success": False, "message": "Cannot connect to the API backend."}), 503
    except Exception as exc:
        logger.exception("Attendance mark error: {}", exc)
        return jsonify({"success": False, "message": str(exc)}), 500