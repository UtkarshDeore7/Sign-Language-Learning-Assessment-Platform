"""
Performance API
===============
GET /api/performance/{student_id} — measure and report inference performance
GET /api/performance/platform      — platform-wide performance stats
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import APIRouter, Depends
from database import get_db
from models import AssessmentAttempt, PracticeSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/performance/{student_id}")
def get_student_performance(student_id: str, db: Session = Depends(get_db)):
    """
    Breakdown of inference latency for a student.
    Identifies bottlenecks in the pipeline.
    """
    attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.student_id == str(student_id)
    ).all()

    if not attempts:
        return {
            "success": True,
            "data": {"message": "No attempts yet.", "student_id": student_id},
            "timestamp": datetime.utcnow().isoformat()
        }

    times = [a.inference_time_ms for a in attempts if a.inference_time_ms]

    avg_ms  = round(sum(times) / len(times), 2)
    min_ms  = round(min(times), 2)
    max_ms  = round(max(times), 2)
    sorted_t = sorted(times)
    p95_ms  = round(sorted_t[int(len(sorted_t) * 0.95)], 2)

    # Estimate FPS (frames that could be processed per second)
    fps = round(1000 / avg_ms, 1) if avg_ms else 0

    # Bottleneck identification
    if avg_ms < 100:
        bottleneck = "None — pipeline is fast"
        recommendation = "Performance is good. No optimization needed."
    elif avg_ms < 200:
        bottleneck = "API/network latency"
        recommendation = "Consider reducing frame resolution or compressing JPEG more aggressively."
    elif avg_ms < 500:
        bottleneck = "MediaPipe landmark extraction"
        recommendation = "Try reducing input frame size to 320x240 before sending to API."
    else:
        bottleneck = "Model inference"
        recommendation = "Consider caching landmark extraction or running MediaPipe client-side."

    return {
        "success": True,
        "data": {
            "student_id":       student_id,
            "total_attempts":   len(attempts),
            "inference_time_ms": {
                "avg": avg_ms,
                "min": min_ms,
                "max": max_ms,
                "p95": p95_ms
            },
            "estimated_fps":    fps,
            "pipeline_stages": {
                "frame_capture":         "~5-10ms   (browser webcam)",
                "base64_encode":         "~5-15ms   (browser canvas)",
                "network_transfer":      "~10-30ms  (HTTP POST)",
                "frame_validation":      "~10-20ms  (brightness + hand check)",
                "mediapipe_extraction":  "~30-80ms  (landmark detection)",
                "model_inference":       "~1-5ms    (Random Forest)",
                "db_write":              "~5-15ms   (PostgreSQL INSERT)",
                "total_measured":        f"~{avg_ms}ms avg"
            },
            "bottleneck":       bottleneck,
            "recommendation":   recommendation
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/performance/platform/stats")
def get_platform_performance(db: Session = Depends(get_db)):
    """Platform-wide performance metrics."""
    result = db.query(
        func.avg(AssessmentAttempt.inference_time_ms).label("avg"),
        func.min(AssessmentAttempt.inference_time_ms).label("min"),
        func.max(AssessmentAttempt.inference_time_ms).label("max"),
        func.count(AssessmentAttempt.id).label("total")
    ).first()

    avg_ms = round(float(result.avg or 0), 2)

    return {
        "success": True,
        "data": {
            "avg_inference_ms": avg_ms,
            "min_inference_ms": round(float(result.min or 0), 2),
            "max_inference_ms": round(float(result.max or 0), 2),
            "total_assessments": result.total,
            "estimated_fps": round(1000 / avg_ms, 1) if avg_ms else 0
        },
        "timestamp": datetime.utcnow().isoformat()
    }