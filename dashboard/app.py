"""
dashboard/app.py — Flask application entry point for the admin dashboard.

The dashboard calls the FastAPI backend for all data — it never touches
Supabase directly.

Run with:
  python dashboard/app.py
or via gunicorn for production.
"""

import os
import sys

# Allow importing from project root regardless of working directory
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from flask import Flask
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from dashboard.routes.home import home_bp
from dashboard.routes.students import students_bp
from dashboard.routes.attendance import attendance_bp
from dashboard.routes.reports import reports_bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")

    # ── Register blueprints ────────────────────────────────────────────────────
    app.register_blueprint(home_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(reports_bp)

    logger.info("Flask dashboard initialised with {} blueprints", 4)
    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info("📊 Dashboard starting on port {}", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
