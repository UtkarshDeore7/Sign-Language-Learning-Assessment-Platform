"""
Dashboard API
=============
GET /api/dashboard/{student_id}  — full real-time dashboard in one call
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.analytics_service import AnalyticsService

router   = APIRouter()
analytics = AnalyticsService()


@router.get("/dashboard/{student_id}")
def get_dashboard(student_id: str, db: Session = Depends(get_db)):
    return analytics.get_dashboard(db, student_id)