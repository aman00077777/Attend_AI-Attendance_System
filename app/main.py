"""
main.py — FastAPI application entry point (Optimized for Low RAM/Render)

Start with:
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager

# ─── TensorFlow RAM Optimization (CRITICAL FOR RENDER) ────────────────────────
# DeepFace import karne se PEHLE yeh settings lagana zaroori hai
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Logs kam karo taaki memory bache
os.environ["AUTOGRAPH_VERBOSITY"] = "0"

import tensorflow as tf
# TensorFlow ko bolo ki memory dynamic allocate kare, pehle se block na kare
import tf_keras

try:
    gpus = tf.config.experimental.list_physical_devices('GPU')
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    # CPU usage ke liye threads limit karein taaki Render memory crash na ho
    tf.config.threading.set_intra_op_parallelism_threads(1)
    tf.config.threading.set_inter_op_parallelism_threads(1)
except Exception:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from deepface import DeepFace

from app.config import get_settings
from app.routers import attendance, students

# ─── Logging ──────────────────────────────────────────────────────────────────
settings = get_settings()
os.makedirs("logs", exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
    colorize=True,
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
        logger.info("⏳ Loading DeepFace Facenet512 weights into memory...")
        
        # Clear keras session before loading to wipe any initial bloat
        tf_keras.backend.clear_session()
        
        await asyncio.to_thread(DeepFace.build_model, "Facenet512")
        logger.info("✅ DeepFace Facenet512 model successfully pre-loaded!")
    except Exception as e:
        logger.error(f"❌ Failed to pre-load DeepFace model: {e}")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(students.router)
app.include_router(attendance.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "attendance-api", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.api_port))
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=port,
        reload=False,  # Production/Render par reload False hona chahiye RAM bachane ke liye
        log_level=settings.log_level.lower(),
    )