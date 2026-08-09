# Sign Language Learning & Assessment Platform

An AI-powered platform that helps users learn American Sign Language (ASL) through real-time gesture recognition, adaptive feedback, and intelligent progress tracking.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI |
| Database (Primary) | PostgreSQL |
| Database (Secondary) | MongoDB |
| ML / Computer Vision | MediaPipe, OpenCV, Scikit-learn |
| ML Model | Random Forest (98.64% accuracy, 87K images, 29 classes) |
| Frontend | HTML, CSS, JavaScript |
| Containerization | Docker, Docker Compose |
| Auth | JWT (python-jose, bcrypt) |

---

## Project Structure

```
Sign-Language-Learning-Assessment-Platform/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI app entry point
│       ├── database.py              # DB connection
│       ├── models.py                # SQLAlchemy ORM models
│       ├── schemas.py               # Pydantic schemas
│       ├── auth.py                  # JWT authentication
│       ├── routes.py                # Auth + profile routes
│       ├── api/                     # API route handlers
│       │   ├── assess_frame.py      # Main assessment endpoint
│       │   ├── sessions.py          # Session management
│       │   ├── learner_state.py     # State machine
│       │   ├── dashboard.py         # Analytics dashboard
│       │   ├── reports.py           # Reports + CSV/PDF export
│       │   ├── progress.py          # Progress tracking
│       │   ├── certification.py     # Scoring + certification
│       │   └── instructor_admin.py  # Instructor + admin views
│       ├── services/                # Business logic
│       │   ├── session_service.py
│       │   ├── learner_state_service.py
│       │   ├── analytics_service.py
│       │   ├── progress_service.py
│       │   ├── report_service.py
│       │   ├── scoring_service.py
│       │   ├── certification_service.py
│       │   ├── feedback_service.py
│       │   ├── instructor_service.py
│       │   └── admin_service.py
│       ├── ai/
│       │   ├── ml/inference/
│       │   │   ├── gesture_engine.py   # Random Forest classifier
│       │   │   └── pipeline.py         # Full prediction pipeline
│       │   └── validation/
│       │       └── frame_validator.py  # Input validation layer
│       └── requirements.txt
├── ml/
│   └── models/
│       ├── gesture_classifier.pkl   # Trained Random Forest (73MB)
│       └── hand_landmarker.task     # MediaPipe hand model
├── frontend/
│   └── index.html                   # Single-page webcam UI
├── backend/tests/
│   └── test_api.py                  # End-to-end test suite
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── .dockerignore
```

---

## Milestones

| Milestone | Scope | Status |
|-----------|-------|--------|
| M1 — Week 1&2 | Project init, auth, learner profile, datasets | ✅ Complete |
| M2 — Week 3&4 | Gesture recognition, assessment, DB, frontend | ✅ Complete |
| M3 — Week 5&6 | Feedback, analytics, recommendations, dashboards | ✅ Complete |
| M4 — Week 7&8 | Certification, Docker, admin dashboards, testing | ✅ Complete |

---

## Local Setup (without Docker)

### Prerequisites
- Python 3.11
- PostgreSQL running locally
- Git

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/springboardmentor8984d-code/Sign-Language-Learning-Assessment-Platform.git
cd Sign-Language-Learning-Assessment-Platform

# 2. Install dependencies
cd backend/app
pip install -r requirements.txt

# 3. Set up environment variables
# Create a .env file in backend/app/ with:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/sign_language_db
# SECRET_KEY=your-secret-key
# ALGORITHM=HS256
# ACCESS_TOKEN_EXPIRE_MINUTES=30

# 4. Create the database
python -c "import psycopg2; conn = psycopg2.connect(host='localhost', user='postgres', password='yourpassword', database='postgres'); conn.autocommit = True; conn.cursor().execute('CREATE DATABASE sign_language_db'); conn.close()"

# 5. Create all tables
python -c "from database import engine; import models; models.Base.metadata.create_all(bind=engine); print('Tables created')"

# 6. Seed roles
# Start the server first, then call: POST /api/admin/seed-roles

# 7. Start the backend
uvicorn main:app --reload

# 8. Start the frontend (new terminal)
cd ../../frontend
python -m http.server 3000
```

Open:
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

---

## Docker Setup

### Prerequisites
- Docker Desktop installed and running

### Steps

```bash
# Build and start all containers
docker-compose up --build

# Stop containers
docker-compose down
```

Services started:
- `http://localhost:3000` — Frontend (nginx)
- `http://localhost:8000` — Backend (FastAPI)
- PostgreSQL on port 5432

---

## Key API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT token |

### Practice Session (Full Autonomous Pipeline)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sessions/start` | Start a practice session |
| POST | `/api/assess/frame` | Submit webcam frame → full pipeline |
| PUT | `/api/sessions/end/{id}` | End session, generate summary |

### Learner State Machine
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/state/{student_id}` | All 26 letter states |
| GET | `/api/state/{student_id}/recommendations` | AI-recommended practice queue |

### Analytics & Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/{student_id}` | Full learner dashboard |
| GET | `/api/progress/{student_id}` | Cross-session trends |

### Reports & Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/student/{id}` | Student Performance Report |
| GET | `/api/reports/student/{id}/export/csv` | Download CSV |
| GET | `/api/reports/student/{id}/export/pdf` | Download PDF |

### Scoring & Certification
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/score/{student_id}` | Weighted Performance Score |
| GET | `/api/certification/{id}/eligibility` | Check cert eligibility |
| POST | `/api/certification/{id}/issue` | Issue certificate |
| GET | `/api/certification/{id}/download` | Download PDF certificate |
| GET | `/api/certification/{id}/badges` | View all badges |

### Instructor & Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/instructor/dashboard` | Class overview |
| GET | `/api/instructor/student/{id}` | Student detail |
| GET | `/api/admin/dashboard` | Platform analytics |
| GET | `/api/admin/users` | User management |
| POST | `/api/admin/seed-roles` | Seed roles |

---

## Autonomous Learning Cycle

Every call to `POST /api/assess/frame` automatically:

1. Validates the webcam frame (brightness, hand detection, landmark completeness)
2. Runs MediaPipe hand tracking → extracts 63 landmark features
3. Classifies gesture with Random Forest (98.64% accuracy)
4. Records attempt in PostgreSQL
5. Updates learner state machine (Not Attempted → Learning → Improving → Mastered → Needs Revision)
6. Updates learner profile analytics
7. Recalculates next recommended letter
8. Generates personalised feedback
9. Returns everything in a single JSON response

No manual intervention required after the frame is submitted.

---

## Weighted Scoring Model

```
Learning Performance Score =
  Gesture Accuracy        × 40%   (overall prediction accuracy)
  Assessment Performance  × 25%   (average session accuracy)
  Lesson Completion       × 15%   (% of alphabet attempted)
  Practice Consistency    × 10%   (active days in last 7 days)
  Skill Improvement Rate  × 10%   (session-to-session accuracy delta)
```

Score ≥ 70 → eligible for ASL Learning Certificate.

---

## Running Tests

```bash
# Install test dependencies
pip install pytest requests

# Run full test suite (server must be running)
cd Sign-Language-Learning-Assessment-Platform
pytest backend/tests/test_api.py -v
```

---

## ML Model

- **Dataset**: ASL Alphabet (87,000 images, 29 classes — A-Z + del/nothing/space)
- **Model**: Random Forest Classifier (scikit-learn)
- **Accuracy**: 98.64% on test set
- **Pipeline**: MediaPipe Hand Landmarker → 63 normalised (x,y,z) features → RF prediction
- **Inference time**: ~45-130ms per frame

---

## Built by

Utkarsh Deore — Computer Science Engineering, MIT Mumbai  
Infosys Springboard Internship 2026