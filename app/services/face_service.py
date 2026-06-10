"""
face_service.py — Core face recognition logic using DeepFace + OpenCV.

Responsibilities:
  • Extract face embeddings from an image (file path or numpy array)
  • Compare a probe embedding against all stored student embeddings
  • Return the best match below the configured distance threshold
"""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path

import cv2
import numpy as np
from deepface import DeepFace
from loguru import logger
from PIL import Image

from app.config import get_settings

settings = get_settings()

# DeepFace model / detector used consistently across the app
_MODEL_NAME = "Facenet512"
_DETECTOR_BACKEND = "opencv"
_DISTANCE_METRIC = "cosine"


def _decode_b64_to_ndarray(image_b64: str) -> np.ndarray:
    """Decode a Base-64 image string to a BGR numpy array."""
    # Strip data-URL prefix if present  (e.g. "data:image/jpeg;base64,…")
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    raw = base64.b64decode(image_b64)
    pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return bgr


def extract_embedding(image_b64: str) -> list[float]:
    """
    Extract a 512-dim face embedding from a Base-64 encoded image.

    Raises:
        ValueError: if no face is detected in the image.

    Returns:
        list[float]: the face embedding vector.
    """
    bgr = _decode_b64_to_ndarray(image_b64)

    # Write to a temp file so DeepFace can read it (some backends need a path)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        cv2.imwrite(tmp_path, bgr)

    try:
        result = DeepFace.represent(
            img_path=tmp_path,
            model_name=_MODEL_NAME,
            detector_backend=_DETECTOR_BACKEND,
            enforce_detection=True,
        )
    except Exception as exc:
        logger.warning("Face not detected: {}", exc)
        raise ValueError("No face detected in the provided image.") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    embedding: list[float] = result[0]["embedding"]
    logger.info("Extracted embedding — dim={}", len(embedding))
    return embedding


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """Compute cosine distance between two embedding vectors."""
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    dot = np.dot(va, vb)
    norm = np.linalg.norm(va) * np.linalg.norm(vb)
    if norm == 0:
        return 1.0
    return float(1.0 - dot / norm)


def find_best_match(
    probe_embedding: list[float],
    students: list[dict],
) -> dict | None:
    """
    Compare probe_embedding against every student's stored face_encoding.

    Args:
        probe_embedding: embedding extracted from the webcam frame.
        students: list of student dicts from Supabase (must include
                  'face_encoding' and at least 'id', 'name', 'roll_number').

    Returns:
        The student dict of the best match (with added '_distance' key),
        or None if no match is below the configured distance threshold.
    """
    threshold = settings.face_match_threshold
    best_dist = float("inf")
    best_student: dict | None = None

    for student in students:
        enc = student.get("face_encoding")
        if not enc:
            continue

        # Supabase JSONB may return a dict with numeric string keys
        if isinstance(enc, dict):
            enc = [enc[str(k)] for k in sorted(enc.keys(), key=int)]

        try:
            dist = _cosine_distance(probe_embedding, enc)
        except Exception as exc:
            logger.warning(
                "Could not compare embedding for student {}: {}", student.get("id"), exc
            )
            continue

        logger.debug(
            "Student {} — cosine distance: {:.4f}", student.get("roll_number"), dist
        )
        if dist < best_dist:
            best_dist = dist
            best_student = student

    if best_student is not None and best_dist <= threshold:
        logger.info(
            "Match found: {} (dist={:.4f}, threshold={})",
            best_student.get("name"),
            best_dist,
            threshold,
        )
        return {**best_student, "_distance": best_dist}

    logger.info(
        "No match found. Best distance: {} > threshold {}",
        f"{best_dist:.4f}" if best_dist != float("inf") else "inf",
        threshold,
    )
    return None
