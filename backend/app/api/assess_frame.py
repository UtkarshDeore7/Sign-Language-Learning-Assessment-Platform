"""
Assess Frame API
================
POST /api/assess/frame

Full autonomous pipeline — one call does everything:
  base64 frame
      ↓  FrameValidator        (quality + hand detection)
      ↓  GestureEngine         (landmark normalise → RF classify)
      ↓  SessionService        (record attempt in DB)
      ↓  LearnerStateService   (state machine update)
      ↓  AnalyticsService      (update learner profile)
      ↓  LearnerStateService   (next recommendation)
      ↓  FeedbackEngine        (personalised feedback)
      ↓  JSON response

No manual intervention needed after this call.
"""

import time
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.session_service       import SessionService
from services.feedback_service      import FeedbackEngine
from services.learner_state_service import LearnerStateService
from services.analytics_service     import AnalyticsService
from ai.validation.frame_validator  import FrameValidator
from ai.ml.inference.gesture_engine import GestureEngine

logger = logging.getLogger(__name__)

PROJECT_ROOT    = Path(__file__).resolve().parent.parent.parent.parent
TASK_MODEL      = PROJECT_ROOT / "ml" / "models" / "hand_landmarker.task"

_validator      = FrameValidator(str(TASK_MODEL))
_gesture_engine = GestureEngine()
_feedback       = FeedbackEngine()
_session_svc    = SessionService()
_state_svc      = LearnerStateService()
_analytics      = AnalyticsService()

router = APIRouter()


class AssessFrameRequest(BaseModel):
    session_id:    str
    student_id:    str
    target_letter: str
    frame_base64:  str


@router.post("/assess/frame")
def assess_frame(request: AssessFrameRequest, db: Session = Depends(get_db)):

    start = time.time()

    # ── 1. Validate frame ─────────────────────────────────────────────────
    validation = _validator.validate(request.frame_base64)

    if not validation.is_valid:
        logger.info(f"Frame rejected | {validation.error_code} | {validation.message}")
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

    # ── 2. Build feature vector ───────────────────────────────────────────
    landmarks      = validation.landmarks
    feature_vector = [v for lm in landmarks for v in [lm.x, lm.y, lm.z]]

    # ── 3. Gesture classification ─────────────────────────────────────────
    pred_result  = _gesture_engine.predict(feature_vector)
    inference_ms = round((time.time() - start) * 1000, 2)

    if pred_result.prediction in ("error", "unknown"):
        logger.warning(f"Prediction failed | {pred_result.error}")
        return {
            "success":    False,
            "message":    "Gesture recognition failed. Please try again.",
            "error_code": "PREDICTION_ERROR",
            "data":       {"detail": pred_result.error},
            "timestamp":  _now()
        }

    predicted_letter = pred_result.prediction
    
    # --- ADD THIS FIX HERE ---
    # Prevent database crash by shrinking the word to fit VARCHAR(5)
    if predicted_letter == "UNCERTAIN":
        predicted_letter = "?"
    # -------------------------
        
    confidence       = pred_result.confidence
    is_correct       = predicted_letter.upper() == request.target_letter.upper()
    
    # ── 4. Record attempt (also updates state machine internally) ─────────
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
        return record_result

    attempt_data = record_result["data"]

    # ── 5. Update learner profile (analytics) ─────────────────────────────
    _analytics.update_learner_profile(db, request.student_id)

    # ── 6. Get next recommendation ────────────────────────────────────────
    recs         = _state_svc.get_recommendations(db, request.student_id)
    next_letter  = recs["data"]["next_letter"]
    rec_queue    = recs["data"]["recommended_queue"][:5]

    # ── 7. Generate personalised feedback ─────────────────────────────────
    feedback      = _feedback.generate_feedback(
        request.target_letter, predicted_letter, confidence
    )
    feedback_data = feedback.get("data", {})

    logger.info(
        f"Assessment | session={request.session_id} | "
        f"{request.target_letter}→{predicted_letter} | "
        f"correct={is_correct} | conf={confidence:.2f} | {inference_ms}ms"
    )

    return {
        "success": True,
        "message": "Frame assessed successfully.",
        "data": {
            # Prediction
            "target_letter":     request.target_letter.upper(),
            "predicted_letter":  predicted_letter.upper(),
            "result":            "✓ Correct!" if is_correct else "✗ Incorrect",
            "is_correct":        is_correct,
            "confidence":        confidence,
            "inference_time_ms": inference_ms,

            # Session stats
            "attempt_number":    attempt_data["attempt_number"],
            "session_accuracy":  attempt_data["session_accuracy"],
            "avg_confidence":    attempt_data["avg_confidence"],
            "correct_total":     attempt_data["correct_total"],
            "incorrect_total":   attempt_data["incorrect_total"],

            # State machine
            "letter_state":      attempt_data.get("letter_state", {}),

            # Autonomous next step
            "next_recommended_letter": next_letter,
            "recommendation_queue":    rec_queue,

            # Feedback
            "feedback": {
                "type":             feedback_data.get("feedback_type", ""),
                "message":          feedback_data.get("feedback_message", ""),
                "correction_tip":   feedback_data.get("correction_tip", ""),
                "sign_instruction": feedback_data.get("sign_instructions", "")
            }
        },
        "timestamp": _now()
    }


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat()