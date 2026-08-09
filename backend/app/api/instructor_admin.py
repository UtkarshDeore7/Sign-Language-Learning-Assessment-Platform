"""
Instructor & Admin API
======================
Instructor routes:
  GET  /api/instructor/dashboard          — class overview
  GET  /api/instructor/student/{id}       — student detail
  GET  /api/instructor/class-progress     — class trend

Admin routes:
  GET  /api/admin/dashboard               — platform stats
  GET  /api/admin/users                   — all users list
  PUT  /api/admin/users/{id}/toggle       — activate/deactivate user
  GET  /api/admin/health                  — system health
  POST /api/admin/seed-roles              — seed role data
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.instructor_service import InstructorService
from services.admin_service      import AdminService

router      = APIRouter()
instructor  = InstructorService()
admin_svc   = AdminService()


# ── Instructor routes ─────────────────────────────────────────────────────────

@router.get("/instructor/dashboard")
def instructor_dashboard(db: Session = Depends(get_db)):
    return instructor.get_class_overview(db)


@router.get("/instructor/student/{student_id}")
def student_detail(student_id: str, db: Session = Depends(get_db)):
    return instructor.get_student_detail(db, student_id)


@router.get("/instructor/class-progress")
def class_progress(db: Session = Depends(get_db)):
    return instructor.get_class_progress(db)


# ── Admin routes ──────────────────────────────────────────────────────────────

@router.get("/admin/dashboard")
def admin_dashboard(db: Session = Depends(get_db)):
    return admin_svc.get_platform_overview(db)


@router.get("/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    return admin_svc.get_all_users(db)


@router.put("/admin/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db)):
    return admin_svc.toggle_user_status(db, user_id)


@router.get("/admin/health")
def system_health(db: Session = Depends(get_db)):
    return admin_svc.get_system_health(db)


@router.post("/admin/seed-roles")
def seed_roles(db: Session = Depends(get_db)):
    return admin_svc.seed_roles(db)