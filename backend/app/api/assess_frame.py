"""
Assess Frame API
================
POST /api/assess/frame

The single endpoint the frontend calls in a loop while the webcam is running.
Full pipeline per request:

  base64 frame
      ↓  FrameValidator   (quality + hand detection)
      ↓  GestureEngine    (landmark normalise → RF classify)
      ↓  SessionService   (record attempt in DB)
      ↓  FeedbackEngine   (personalised feedback + correction tip)
      ↓  JSON response

No page refresh or manual step needed — one call does everything.
"""

import time
import logging
import numpy as np
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.session_service import SessionService
from services.feedback_service import FeedbackEngine
from ai.validation.frame_validator import FrameValidator
from ai.ml.inference.gesture_engine import GestureEngine

logger = logging.getLogger(__name__)

# ─── Singletons (loaded once at startup) ─────────────────────────────────────

PROJECT_ROOT   = Path(__file__).resolve().parent.parent.parent.parent
TASK_MODEL     = PROJECT_ROOT / "ml" / "models" / "hand_landmarker.task"

_validator      = FrameValidator(str(TASK_MODEL))
_gesture_engine = GestureEngine()
_feedback       = FeedbackEngine()
_session_svc    = SessionService()

router = APIRouter()


# ─── Request / Response models ────────────────────────────────────────────────

class AssessFrameRequest(BaseModel):
    session_id:    str
    student_id:    str
    target_letter: str
    frame_base64:  str      # webcam snapshot as base64 JPEG/PNG


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/assess/frame")
def assess_frame(request: AssessFrameRequest, db: Session = Depends(get_db)):
    """
    Full assessment pipeline for one webcam frame.
    Called by the frontend every time the learner wants to submit a sign.
    """
    start = time.time()

    # ── 1. Validate frame ─────────────────────────────────────────────────
    validation = _validator.validate(request.frame_base64)

    if not validation.is_valid:
        logger.info(
            f"Frame rejected | session={request.session_id} | "
            f"code={validation.error_code} | msg={validation.message}"
        )
        return {
            "success":    False,
            "message":    validation.message,
            "error_code": validation.error_code,
            "data": {
                "hand_detected": validation.hand_detected,
                "frame_valid":   validation.frame_valid,
                "action":        "Fix the issue above, then try again."
            },
            "timestamp": _now()
        }

    # ── 2. Build feature vector from validated landmarks ──────────────────
    landmarks = validation.landmarks          # list of 21 NormalizedLandmark
    feature_vector = _landmarks_to_vector(landmarks)

    # ── 3. Run gesture classifier ─────────────────────────────────────────
    pred_result = _gesture_engine.predict(feature_vector)
    inference_ms = round((time.time() - start) * 1000, 2)

    if pred_result.prediction in ("error", "unknown"):
        logger.warning(
            f"Prediction failed | session={request.session_id} | "
            f"error={pred_result.error}"
        )
        return {
            "success":    False,
            "message":    "Gesture recognition failed. Please try again.",
            "error_code": "PREDICTION_ERROR",
            "data":       {"detail": pred_result.error},
            "timestamp":  _now()
        }

    predicted_letter = pred_result.prediction
    confidence       = pred_result.confidence
    is_correct       = predicted_letter.upper() == request.target_letter.upper()

    # ── 4. Record attempt in DB (via SessionService) ──────────────────────
    record_result = _session_svc.record_attempt(
        db,
        session_id        = request.session_id,
        student_id        = request.student_id,
        target_letter     = request.target_letter,
        predicted_letter  = predicted_letter,
        is_correct        = is_correct,
        confidence        = confidence,
        inference_time_ms = inference_ms,
        hand_detected     = True,
        frame_valid       = True
    )

    if not record_result["success"]:
        return record_result   # propagate session-not-found or completed errors

    attempt_data = record_result["data"]

    # ── 5. Generate personalised feedback ─────────────────────────────────
    feedback = _feedback.generate_feedback(
        expected   = request.target_letter,
        predicted  = predicted_letter,
        confidence = confidence
    )
    feedback_data = feedback["data"]

    # ── 6. Build response ─────────────────────────────────────────────────
    logger.info(
        f"Assessment | session={request.session_id} | "
        f"target={request.target_letter} predicted={predicted_letter} "
        f"correct={is_correct} conf={confidence:.2f} time={inference_ms}ms"
    )

    return {
        "success": True,
        "message": "Frame assessed successfully.",
        "data": {
            # Prediction result
            "target_letter":    request.target_letter.upper(),
            "predicted_letter": predicted_letter.upper(),
            "result":           "✓ Correct!" if is_correct else "✗ Incorrect",
            "is_correct":       is_correct,
            "confidence":       confidence,
            "inference_time_ms": inference_ms,

            # Attempt stats (from session)
            "attempt_number":   attempt_data["attempt_number"],
            "session_accuracy": attempt_data["session_accuracy"],
            "avg_confidence":   attempt_data["avg_confidence"],
            "correct_total":    attempt_data["correct_total"],
            "incorrect_total":  attempt_data["incorrect_total"],

            # Personalised feedback
            "feedback": {
                "type":           feedback_data["feedback_type"],
                "message":        feedback_data["feedback_message"],
                "correction_tip": feedback_data["correction_tip"],
                "sign_instruction": feedback_data["sign_instructions"]
            }
        },
        "timestamp": _now()
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _landmarks_to_vector(landmarks) -> list:
    """
    Convert MediaPipe NormalizedLandmark list → flat [x,y,z] * 21 = 63 floats.
    Matches the format GestureEngine._normalize() expects.
    """
    return [v for lm in landmarks for v in [lm.x, lm.y, lm.z]]


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()