"""
main.py — FastAPI application entry point.

Start with:
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from deepface import DeepFace

from app.config import get_settings
from app.routers import attendance, students

# ─── Logging ──────────────────────────────────────────────────────────────────
settings = get_settings()

# Ensure logs directory exists before loguru tries to create the file sink
os.makedirs("logs", exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
    colorize=True,
)
logger.add(
    "logs/api.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO",
    compression="zip",
)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "🚀 Face Recognition Attendance API starting on {}:{}",
        settings.api_host,
        settings.api_port,
    )
    
    # ─── DeepFace Model Pre-loading ───
    try:
        logger.info("⏳ Downloading/Loading DeepFace Facenet512 weights on startup...")
        
        # CPU par execution safe rakhne aur event loop ko block na karne ke liye thread mein run karenge
        await asyncio.to_thread(DeepFace.build_model, "Facenet512")
        
        logger.info("✅ DeepFace Facenet512 model successfully pre-loaded!")
    except Exception as e:
        logger.error(f"❌ Failed to pre-load DeepFace model: {e}")
    # ──────────────────────────────────

    yield
    logger.info("🛑 API shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Face Recognition Attendance System",
    description="REST API for automated attendance marking using DeepFace.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Flask dashboard to call this API
# NOTE: allow_origins=["*"] is incompatible with allow_credentials=True
# (browsers reject it per the CORS spec). Use explicit origins or no credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(students.router)
app.include_router(attendance.router)


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "attendance-api", "version": "1.0.0"}


# ─── Run directly ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )