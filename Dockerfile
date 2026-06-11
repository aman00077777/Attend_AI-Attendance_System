# ── FastAPI Backend Dockerfile ────────────────────────────────────────────────
FROM python:3.11-slim

# System deps for OpenCV / DeepFace
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app/ ./app/
# Agar aap HF Secrets use kar rahe hain, toh is line ko hata dein
COPY .env .env 

# Create directories
RUN mkdir -p known_faces logs

# Hugging Face ke liye Port 7860 expose karein
EXPOSE 7860

# Uvicorn ko Port 7860 par run karein
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]