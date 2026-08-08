"""
Reports & Progress API
======================
Reports:
  GET /api/reports/student/{student_id}            — Student Performance Report (JSON)
  GET /api/reports/session/{session_id}            — Session Report (JSON)
  GET /api/reports/student/{student_id}/export/csv — Download all attempts as CSV
  GET /api/reports/student/{student_id}/export/pdf — Download Performance Report as PDF

Progress:
  GET /api/progress/{student_id}                   — Cross-session overview
  GET /api/progress/{student_id}/summary/{session_id} — Progress summary for one session
  GET /api/progress/{student_id}/alphabet-trends   — Per-letter accuracy over time
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import io

from sqlalchemy.orm import Session

from database import get_db
from services.report_service   import ReportService
from services.progress_service import ProgressService

router   = APIRouter()
reports  = ReportService()
progress = ProgressService()


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/student/{student_id}")
def student_performance_report(student_id: str, db: Session = Depends(get_db)):
    return reports.get_student_performance_report(db, student_id)


@router.get("/reports/session/{session_id}")
def session_report(session_id: str, db: Session = Depends(get_db)):
    return reports.get_session_report(db, session_id)


@router.get("/reports/student/{student_id}/export/csv")
def export_csv(student_id: str, db: Session = Depends(get_db)):
    csv_bytes = reports.export_student_csv(db, student_id)
    filename  = f"student_{student_id}_report.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/reports/session/{session_id}/export/csv")
def export_session_csv(session_id: str, db: Session = Depends(get_db)):
    csv_bytes = reports.export_session_csv(db, session_id)
    filename  = f"session_{session_id}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/reports/student/{student_id}/export/pdf")
def export_pdf(student_id: str, db: Session = Depends(get_db)):
    try:
        pdf_bytes = reports.export_student_pdf(db, student_id)
        filename  = f"student_{student_id}_report.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except RuntimeError as e:
        return {"success": False, "message": str(e), "data": None}


# ── Progress ──────────────────────────────────────────────────────────────────

@router.get("/progress/{student_id}")
def progress_overview(student_id: str, db: Session = Depends(get_db)):
    return progress.get_progress_overview(db, student_id)


@router.get("/progress/{student_id}/summary/{session_id}")
def session_progress_summary(
    student_id: str, session_id: str, db: Session = Depends(get_db)
):
    return progress.get_session_progress_summary(db, student_id, session_id)


@router.get("/progress/{student_id}/alphabet-trends")
def alphabet_trends(student_id: str, db: Session = Depends(get_db)):
    return progress.get_alphabet_trends(db, student_id)