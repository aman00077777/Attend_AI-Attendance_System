# AttendAI — Face Recognition Attendance System

An end-to-end automated attendance system powered by DeepFace facial recognition, FastAPI, and Supabase. Students are identified in real time via webcam and attendance is marked instantly through a modern dark-themed web dashboard.

## Live Demo

- **Dashboard (Frontend):** [https://attend-ai-bv0g.onrender.com](https://attend-ai-bv0g.onrender.com)
- **API (Backend):** [https://aman20061203-attend-ai-backend.hf.space](https://aman20061203-attend-ai-backend.hf.space)
- **API Docs:** [https://aman20061203-attend-ai-backend.hf.space/docs](https://aman20061203-attend-ai-backend.hf.space/docs)

---

## Features

| Feature | Details |
|---------|---------|
| Student Registration | Webcam capture or photo upload → face embedding via DeepFace (Facenet512) |
| Live Attendance | Real-time webcam → capture frame → identify face → mark attendance |
| Deduplication | Prevents double attendance per student, subject, and day |
| Reports | Filter by date, student, subject · attendance % per student |
| Charts | 30-day trend · attendance distribution donut · daily bar chart |
| Exports | PDF (ReportLab) · CSV download |
| Low Attendance Alerts | Dashboard flags students below 75% attendance |
| Dark Dashboard | Glassmorphism design · Bootstrap 5 · mobile responsive |

---

## Architecture

```
Browser (Dashboard)  ←→  Flask (Render)  ←→  FastAPI (Hugging Face)  ←→  Supabase
```

- **FastAPI (AI Backend)** handles all heavy ML processing (Face Recognition) and database operations, hosted on Hugging Face's powerful cloud.
- **Flask (Frontend)** serves the UI and proxies API calls, hosted seamlessly on Render.
- **DeepFace + Facenet512** extracts 512-dimensional face embeddings.
- **Supabase** stores students, embeddings (JSONB), attendance records, and photos.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI / ML | DeepFace, OpenCV, NumPy |
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Dashboard | Flask, Jinja2, Bootstrap 5 |
| Database | Supabase (PostgreSQL) |
| Storage | Supabase Storage |
| Charts | Chart.js |
| PDF Export | ReportLab |
| Deployment | Hugging Face Spaces (Docker), Render |

---

## Prerequisites

- Python 3.10+
- [Supabase account](https://supabase.com) (free tier)
- Hugging Face Account (for Backend hosting)
- Render Account (for Dashboard hosting)
- Webcam (for live attendance marking)

---

## Quick Start (Local Development)

### 1. Clone and set up environment

```bash
git clone https://github.com/aman00077777/Attend_AI-Attendance_System.git
cd Attend_AI-Attendance_System
```

### 2. Create Supabase database

- Create a new project at [supabase.com](https://supabase.com)
- Go to **SQL Editor** → paste and run `sql/schema.sql`
- Go to **Storage** → create a bucket named `student-photos` with public access
- Copy your keys from **Settings → API**

### 3. Configure environment variables

Since the architecture is decoupled, environment variables are split.

Create a `.env` file in the root for the **Backend**:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
FACE_MATCH_THRESHOLD=0.6
```

Create a `.env` file in the `dashboard/` folder for the **Frontend**:

```env
API_BASE_URL=http://localhost:8000
FLASK_PORT=5000
SECRET_KEY=any-secure-random-string
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Start the backend

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 6. Start the dashboard

```bash
python dashboard/app.py
```

Dashboard at: [http://localhost:5000](http://localhost:5000)

---

## Deployment Guide

### Phase 1: Backend (Hugging Face Spaces)

The backend requires heavy processing power for DeepFace, making Hugging Face Spaces the ideal free host.

1. Create a new Space on Hugging Face and select **Docker** as the Space SDK.
2. Choose **Blank** template.
3. Upload your backend files (`app/` folder, `requirements.txt`, `Dockerfile`).
4. **Important:** Remove `COPY .env .env` from the Dockerfile if it exists.
5. Go to **Space Settings > Variables and secrets** and add your Supabase Keys.
6. Once the build is "Running", note your new Space URL.

### Phase 2: Dashboard (Render)

The lightweight dashboard is hosted on Render.

1. Update the `API_BASE_URL` in your frontend code (or local `.env`) to point to your new Hugging Face Space URL.
2. Push your code to GitHub.
3. Create a **New Web Service** on Render and connect your repo.
4. Start Command: `gunicorn dashboard.app:app`
5. Add Environment Variables in Render Dashboard:
   - `API_BASE_URL` : Your Hugging Face Space URL
   - `SECRET_KEY` : A random string for Flask sessions
   - `PORT` : `10000` *(Crucial to prevent 502 Bad Gateway errors)*
6. Deploy and access your live attendance system!

---

## API Reference

### Students

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/students/register` | Register student with photo |
| GET | `/api/students/` | List all students |
| GET | `/api/students/{id}` | Get single student |
| DELETE | `/api/students/{id}` | Delete student |

### Attendance

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/attendance/mark` | Mark attendance via base64 image |
| GET | `/api/attendance/today` | Today's attendance records |
| GET | `/api/attendance/report` | Filtered report |
| GET | `/api/attendance/stats` | Attendance % per student |
| GET | `/api/attendance/trend` | 30-day daily counts |
| GET | `/api/attendance/export/csv` | CSV export |

---

## Face Recognition Details

| Parameter | Value |
|-----------|-------|
| Model | Facenet512 (512-dimensional embeddings) |
| Detector | OpenCV (no dlib required) |
| Metric | Cosine distance |
| Threshold | 0.6 (configurable) |
| Storage | Embeddings stored as JSONB in Supabase |

---

## Author

**Aman Sharma**
- GitHub: [aman00077777](https://github.com/aman00077777)
- Fiverr: Available for freelance AI/ML development. Let's connect!

---

## License

MIT