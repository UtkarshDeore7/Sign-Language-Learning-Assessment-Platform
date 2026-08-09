"""
Certification & Scoring API
============================
GET  /api/score/{student_id}                   — weighted performance score breakdown
GET  /api/certification/{student_id}/eligibility — check if eligible
POST /api/certification/{student_id}/issue      — issue certificate
GET  /api/certification/{student_id}/download   — download PDF certificate
GET  /api/certification/{student_id}/badges     — all badges (earned + unearned)
POST /api/certification/{student_id}/badges/evaluate — evaluate + award new badges
"""

import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from services.scoring_service       import ScoringService
from services.certification_service import CertificationService

router  = APIRouter()
scoring = ScoringService()
cert_svc = CertificationService()


@router.get("/score/{student_id}")
def get_performance_score(student_id: str, db: Session = Depends(get_db)):
    return scoring.calculate_performance_score(db, student_id)


@router.get("/certification/{student_id}/eligibility")
def check_eligibility(student_id: str, db: Session = Depends(get_db)):
    return cert_svc.check_eligibility(db, student_id)


@router.post("/certification/{student_id}/issue")
def issue_certificate(student_id: str, db: Session = Depends(get_db)):
    return cert_svc.issue_certificate(db, student_id)


@router.get("/certification/{student_id}/download")
def download_certificate(student_id: str, db: Session = Depends(get_db)):
    try:
        pdf = cert_svc.generate_pdf_certificate(db, student_id)
        return StreamingResponse(
            io.BytesIO(pdf),
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f"attachment; filename=certificate_{student_id}.pdf"
            }
        )
    except (ValueError, RuntimeError) as e:
        return {"success": False, "message": str(e), "data": None}


@router.get("/certification/{student_id}/badges")
def get_badges(student_id: str, db: Session = Depends(get_db)):
    return cert_svc.get_badges(db, student_id)


@router.post("/certification/{student_id}/badges/evaluate")
def evaluate_badges(student_id: str, db: Session = Depends(get_db)):
    return cert_svc.evaluate_and_award_badges(db, student_id)