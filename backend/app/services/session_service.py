"""
Session Service — updated with learner state machine wired in.
"""

import uuid
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from models import PracticeSession, AssessmentAttempt, SessionSummary, ProgressMetrics
from services.learner_state_service import LearnerStateService

logger = logging.getLogger(__name__)
_state_svc = LearnerStateService()


def _session_not_found(session_id):
    return {"success": False, "message": f"Session '{session_id}' not found.",
            "data": None, "timestamp": datetime.utcnow().isoformat()}

def _ok(message, data):
    return {"success": True, "message": message, "data": data,
            "timestamp": datetime.utcnow().isoformat()}


class SessionService:

    def start_session(self, db: Session, student_id: str) -> dict:
        session_id = str(uuid.uuid4())
        practice_session = PracticeSession(
            session_id=session_id, student_id=str(student_id),
            start_time=datetime.utcnow(), status="active"
        )
        db.add(practice_session)
        db.commit()
        db.refresh(practice_session)
        logger.info(f"Session started | student={student_id} | session={session_id}")
        return _ok("Practice session started.", {
            "session_id": session_id, "student_id": student_id,
            "start_time": practice_session.start_time.isoformat(), "status": "active"
        })

    def record_attempt(self, db: Session, session_id: str, student_id: str,
                       target_letter: str, predicted_letter: str, is_correct: bool,
                       confidence: float, inference_time_ms: float,
                       hand_detected: bool = True, frame_valid: bool = True) -> dict:

        session = db.query(PracticeSession).filter(
            PracticeSession.session_id == session_id).first()
        if not session:
            return _session_not_found(session_id)
        if session.status != "active":
            return {"success": False, "message": "Session is already completed.",
                    "data": None, "timestamp": datetime.utcnow().isoformat()}
        if not hand_detected or not frame_valid:
            return {"success": False, "message": "Frame rejected — hand not visible.",
                    "data": {"hand_detected": hand_detected, "frame_valid": frame_valid,
                             "action": "Position your hand clearly in the camera."},
                    "timestamp": datetime.utcnow().isoformat()}

        attempt_number   = session.total_attempts + 1
        gesture_accuracy = round(confidence * 100, 2) if is_correct else round((1 - confidence) * 100, 2)

        attempt = AssessmentAttempt(
            attempt_id=str(uuid.uuid4()), session_id=session_id,
            student_id=str(student_id), target_letter=target_letter.upper(),
            predicted_letter=predicted_letter.upper(), is_correct=is_correct,
            confidence=round(confidence, 4), inference_time_ms=round(inference_time_ms, 2),
            gesture_accuracy=gesture_accuracy, hand_detected=hand_detected,
            frame_valid=frame_valid, attempt_number=attempt_number, timestamp=datetime.utcnow()
        )
        db.add(attempt)

        session.total_attempts     += 1
        session.correct_attempts   += 1 if is_correct else 0
        session.incorrect_attempts += 0 if is_correct else 1
        session.session_accuracy    = round((session.correct_attempts / session.total_attempts) * 100, 2)

        all_conf  = [a.confidence for a in session.attempts] + [confidence]
        session.avg_confidence = round(sum(all_conf) / len(all_conf), 4)

        all_times = [a.inference_time_ms for a in session.attempts] + [inference_time_ms]
        session.avg_inference_time = round(sum(all_times) / len(all_times), 2)

        letters = set(json.loads(session.letters_practiced or "[]"))
        letters.add(target_letter.upper())
        session.letters_practiced = json.dumps(sorted(letters))

        db.commit()
        db.refresh(attempt)

        # Update learner state machine after every attempt
        state_update = _state_svc.update_state(db, student_id, target_letter, is_correct, confidence)

        logger.info(f"Attempt | session={session_id} | {target_letter}→{predicted_letter} "
                    f"| correct={is_correct} | state={state_update['state']}")

        return _ok("Attempt recorded.", {
            "attempt_id": attempt.attempt_id, "attempt_number": attempt_number,
            "target_letter": target_letter.upper(), "predicted_letter": predicted_letter.upper(),
            "result": "✓ Correct!" if is_correct else "✗ Incorrect",
            "is_correct": is_correct, "confidence": attempt.confidence,
            "gesture_accuracy": gesture_accuracy, "inference_time_ms": attempt.inference_time_ms,
            "session_accuracy": session.session_accuracy, "avg_confidence": session.avg_confidence,
            "correct_total": session.correct_attempts, "incorrect_total": session.incorrect_attempts,
            "letter_state": state_update
        })

    def end_session(self, db: Session, session_id: str) -> dict:
        session = db.query(PracticeSession).filter(
            PracticeSession.session_id == session_id).first()
        if not session:
            return _session_not_found(session_id)
        if session.status == "completed":
            return _ok("Session already completed.", {"session_id": session_id, "status": "completed"})

        session.end_time            = datetime.utcnow()
        session.total_duration_secs = round((session.end_time - session.start_time).total_seconds(), 2)
        session.status              = "completed"
        db.commit()

        summary = self._generate_summary(db, session)
        self._record_progress_metrics(db, session)
        # Auto-evaluate badges after every session
        from services.certification_service import CertificationService
        CertificationService().evaluate_and_award_badges(db, session.student_id)
        logger.info(f"Session ended | {session_id} | acc={session.session_accuracy}%")

        return _ok("Session ended. Summary generated.", {
            "session_id": session_id, "status": "completed",
            "duration_seconds": session.total_duration_secs,
            "total_attempts": session.total_attempts, "correct": session.correct_attempts,
            "incorrect": session.incorrect_attempts, "session_accuracy": session.session_accuracy,
            "avg_confidence": session.avg_confidence, "summary": summary
        })

    def get_session(self, db: Session, session_id: str) -> dict:
        session = db.query(PracticeSession).filter(
            PracticeSession.session_id == session_id).first()
        if not session:
            return _session_not_found(session_id)
        return _ok("Session fetched.", {
            "session_id": session.session_id, "student_id": session.student_id,
            "status": session.status, "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "total_duration_secs": session.total_duration_secs,
            "total_attempts": session.total_attempts,
            "correct_attempts": session.correct_attempts,
            "incorrect_attempts": session.incorrect_attempts,
            "session_accuracy": session.session_accuracy,
            "avg_confidence": session.avg_confidence,
            "avg_inference_time": session.avg_inference_time,
            "letters_practiced": json.loads(session.letters_practiced or "[]")
        })

    def get_student_sessions(self, db: Session, student_id: str, limit: int = 20) -> dict:
        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == str(student_id)
        ).order_by(PracticeSession.created_at.desc()).limit(limit).all()
        return _ok("Sessions fetched.", {
            "student_id": student_id, "total_sessions": len(sessions),
            "sessions": [{"session_id": s.session_id, "status": s.status,
                           "start_time": s.start_time.isoformat(),
                           "total_attempts": s.total_attempts,
                           "session_accuracy": s.session_accuracy,
                           "avg_confidence": s.avg_confidence,
                           "duration_seconds": s.total_duration_secs} for s in sessions]
        })

    def _generate_summary(self, db: Session, session: PracticeSession) -> dict:
        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.session_id == session.session_id).all()
        if not attempts:
            return {}
        letter_stats = {}
        for a in attempts:
            if a.target_letter not in letter_stats:
                letter_stats[a.target_letter] = {"correct": 0, "total": 0}
            letter_stats[a.target_letter]["total"] += 1
            if a.is_correct:
                letter_stats[a.target_letter]["correct"] += 1
        letter_accuracy = {l: round((s["correct"]/s["total"])*100, 2) for l, s in letter_stats.items()}
        sorted_acc = sorted(letter_accuracy.items(), key=lambda x: x[1])
        strongest = [l for l, _ in sorted_acc[-3:][::-1]]
        weakest   = [l for l, _ in sorted_acc[:3]]
        recommendations = [f"Practice '{l}' — accuracy {letter_accuracy[l]}%" for l in weakest if letter_accuracy[l] < 100]

        existing = db.query(SessionSummary).filter(SessionSummary.session_id == session.session_id).first()
        if existing:
            db.delete(existing); db.commit()

        db.add(SessionSummary(
            session_id=session.session_id, student_id=session.student_id,
            overall_accuracy=session.session_accuracy, total_attempts=session.total_attempts,
            correct=session.correct_attempts, incorrect=session.incorrect_attempts,
            avg_confidence=session.avg_confidence, avg_inference_time=session.avg_inference_time,
            duration_seconds=session.total_duration_secs,
            strongest_letters=json.dumps(strongest), weakest_letters=json.dumps(weakest),
            recommendations=json.dumps(recommendations), generated_at=datetime.utcnow()
        ))
        db.commit()
        return {"overall_accuracy": session.session_accuracy, "total_attempts": session.total_attempts,
                "correct": session.correct_attempts, "incorrect": session.incorrect_attempts,
                "avg_confidence": session.avg_confidence, "duration_seconds": session.total_duration_secs,
                "strongest_letters": strongest, "weakest_letters": weakest,
                "letter_accuracy": letter_accuracy, "recommendations": recommendations}

    def _record_progress_metrics(self, db: Session, session: PracticeSession):
        prev = db.query(PracticeSession).filter(
            PracticeSession.student_id == session.student_id,
            PracticeSession.status == "completed",
            PracticeSession.session_id != session.session_id
        ).order_by(PracticeSession.created_at.desc()).all()

        n          = len(prev) + 1
        prev_acc   = prev[0].session_accuracy if prev else None
        prev_conf  = prev[0].avg_confidence   if prev else None
        acc_delta  = round(session.session_accuracy - prev_acc,  2) if prev_acc  is not None else 0.0
        conf_delta = round(session.avg_confidence   - prev_conf, 4) if prev_conf is not None else 0.0

        db.add(ProgressMetrics(
            student_id=session.student_id, session_id=session.session_id,
            session_number=n, session_accuracy=session.session_accuracy,
            prev_session_accuracy=prev_acc, accuracy_delta=acc_delta,
            avg_confidence=session.avg_confidence, prev_avg_confidence=prev_conf,
            confidence_delta=conf_delta,
            letters_practiced_count=len(json.loads(session.letters_practiced or "[]")),
            recorded_at=datetime.utcnow()
        ))
        db.commit()
        logger.info(f"Progress | student={session.student_id} | session #{n} | acc={session.session_accuracy}% (Δ{acc_delta:+.2f})")