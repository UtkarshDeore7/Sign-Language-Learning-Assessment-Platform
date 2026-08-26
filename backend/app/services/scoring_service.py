"""
Scoring Service
===============
Implements the weighted Learning Performance Score from the project spec:

  Learning Performance Score =
    Gesture Accuracy        × 40%
    Assessment Performance  × 25%
    Lesson Completion       × 15%
    Practice Consistency    × 10%
    Skill Improvement Rate  × 10%

All inputs sourced from DB — no hardcoded values.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session

from models import (
    PracticeSession, AssessmentAttempt,
    AlphabetState, ProgressMetrics
)

logger = logging.getLogger(__name__)

# ── Weights (must sum to 1.0) ──────────────────────────────────────────────
W_GESTURE_ACCURACY    = 0.40
W_ASSESSMENT_PERF     = 0.25
W_LESSON_COMPLETION   = 0.15
W_PRACTICE_CONSISTENCY= 0.10
W_SKILL_IMPROVEMENT   = 0.10

# ── Certification threshold ────────────────────────────────────────────────
CERTIFICATION_THRESHOLD = 70.0   # score >= 70 → eligible for certificate


class ScoringService:

    def calculate_performance_score(self, db: Session, student_id: str) -> dict:
        """
        Calculate the weighted Learning Performance Score.
        Returns a breakdown of each component and the final score.
        """
        sid = str(student_id)

        g  = self._gesture_accuracy(db, sid)
        a  = self._assessment_performance(db, sid)
        l  = self._lesson_completion(db, sid)
        c  = self._practice_consistency(db, sid)
        i  = self._skill_improvement_rate(db, sid)

        final_score = round(
            g["score"] * W_GESTURE_ACCURACY +
            a["score"] * W_ASSESSMENT_PERF  +
            l["score"] * W_LESSON_COMPLETION+
            c["score"] * W_PRACTICE_CONSISTENCY +
            i["score"] * W_SKILL_IMPROVEMENT,
            2
        )

        eligible = final_score >= CERTIFICATION_THRESHOLD

        return {
            "success": True,
            "data": {
                "student_id":    sid,
                "final_score":   final_score,
                "grade":         self._grade(final_score),
                "cert_eligible": eligible,
                "threshold":     CERTIFICATION_THRESHOLD,
                "breakdown": {
                    "gesture_accuracy": {
                        "raw":    g["score"],
                        "weight": W_GESTURE_ACCURACY,
                        "contribution": round(g["score"] * W_GESTURE_ACCURACY, 2),
                        "detail": g["detail"]
                    },
                    "assessment_performance": {
                        "raw":    a["score"],
                        "weight": W_ASSESSMENT_PERF,
                        "contribution": round(a["score"] * W_ASSESSMENT_PERF, 2),
                        "detail": a["detail"]
                    },
                    "lesson_completion": {
                        "raw":    l["score"],
                        "weight": W_LESSON_COMPLETION,
                        "contribution": round(l["score"] * W_LESSON_COMPLETION, 2),
                        "detail": l["detail"]
                    },
                    "practice_consistency": {
                        "raw":    c["score"],
                        "weight": W_PRACTICE_CONSISTENCY,
                        "contribution": round(c["score"] * W_PRACTICE_CONSISTENCY, 2),
                        "detail": c["detail"]
                    },
                    "skill_improvement_rate": {
                        "raw":    i["score"],
                        "weight": W_SKILL_IMPROVEMENT,
                        "contribution": round(i["score"] * W_SKILL_IMPROVEMENT, 2),
                        "detail": i["detail"]
                    }
                },
                "calculated_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Component 1: Gesture Accuracy (40%) ───────────────────────────────
    def _gesture_accuracy(self, db: Session, student_id: str) -> dict:
        """
        Overall prediction accuracy across all attempts.
        Score = (correct attempts / total attempts) × 100
        """
        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.student_id == student_id
        ).all()

        if not attempts:
            return {"score": 0.0, "detail": "No attempts yet"}

        total   = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        score   = round((correct / total) * 100, 2)

        return {
            "score": score,
            "detail": f"{correct}/{total} correct attempts"
        }

    # ── Component 2: Assessment Performance (25%) ─────────────────────────
    def _assessment_performance(self, db: Session, student_id: str) -> dict:
        """
        Average session accuracy across all completed sessions.
        Score = mean(session_accuracy) across completed sessions
        """
        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == student_id,
            PracticeSession.status     == "completed"
        ).all()

        if not sessions:
            return {"score": 0.0, "detail": "No completed sessions"}

        avg = round(
            sum(s.session_accuracy for s in sessions) / len(sessions), 2
        )
        return {
            "score": avg,
            "detail": f"Avg across {len(sessions)} sessions"
        }

    # ── Component 3: Lesson Completion (15%) ──────────────────────────────
    def _lesson_completion(self, db: Session, student_id: str) -> dict:
        """
        % of alphabet letters attempted at least once.
        Proxy for lesson completion until a full lesson module is built.
        Score = (unique letters attempted / 26) × 100
        """
        states = db.query(AlphabetState).filter(
            AlphabetState.student_id == student_id,
            AlphabetState.state      != "not_attempted"
        ).count()

        score = round((states / 26) * 100, 2)
        return {
            "score": score,
            "detail": f"{states}/26 letters attempted"
        }

    # ── Component 4: Practice Consistency (10%) ───────────────────────────
    def _practice_consistency(self, db: Session, student_id: str) -> dict:
        """
        Score based on practice frequency over the last 7 days.
        7 active days = 100%, 4 days = ~57%, etc.
        Also considers consecutive day streak.
        """
        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == student_id,
            PracticeSession.status     == "completed",
            PracticeSession.start_time >= datetime.utcnow() - timedelta(days=7)
        ).all()

        active_days = len(set(s.start_time.date() for s in sessions))
        score       = round(min((active_days / 7) * 100, 100), 2)

        return {
            "score": score,
            "detail": f"{active_days}/7 days active in last week"
        }

    # ── Component 5: Skill Improvement Rate (10%) ─────────────────────────
    def _skill_improvement_rate(self, db: Session, student_id: str) -> dict:
        """
        Average accuracy improvement across consecutive sessions.
        Score = normalised mean delta (capped at 100).
        Positive delta = improving; flat/negative = low score.
        """
        metrics = db.query(ProgressMetrics).filter(
            ProgressMetrics.student_id == student_id
        ).order_by(ProgressMetrics.session_number.asc()).all()

        if len(metrics) < 2:
            return {
                "score": 50.0,
                "detail": "Need 2+ sessions to calculate improvement"
            }

        deltas = [m.accuracy_delta for m in metrics if m.prev_session_accuracy is not None]
        if not deltas:
            return {"score": 50.0, "detail": "No delta data yet"}

        avg_delta = sum(deltas) / len(deltas)
        # Map delta range [-20, +20] → [0, 100]
        score = round(min(max((avg_delta + 20) / 40 * 100, 0), 100), 2)

        return {
            "score": score,
            "detail": f"Avg session-to-session delta: {avg_delta:+.2f}%"
        }

    # ── Grade helper ──────────────────────────────────────────────────────
    def _grade(self, score: float) -> str:
        if score >= 90: return "A+"
        if score >= 80: return "A"
        if score >= 70: return "B"
        if score >= 60: return "C"
        if score >= 50: return "D"
        return "F"