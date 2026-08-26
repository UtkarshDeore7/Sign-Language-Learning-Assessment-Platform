"""
Instructor Service
==================
Powers the Instructor Dashboard:
  - All students overview
  - Per-student performance
  - Class-wide accuracy and progress
  - Struggling vs top performers
  - Assessment reports across the class
"""

import logging
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session

from models import (
    User, LearnerProfile, PracticeSession,
    AssessmentAttempt, AlphabetState, ProgressMetrics
)
from services.scoring_service import ScoringService

logger  = logging.getLogger(__name__)
scoring = ScoringService()


class InstructorService:

    # ── Class overview ─────────────────────────────────────────────────────

    def get_class_overview(self, db: Session) -> dict:
        """
        Returns a summary of all learners on the platform.
        Used as the main instructor dashboard view.
        """
        all_users = db.query(User).filter(User.is_active == True).all()

        students     = []
        class_accs   = []
        class_scores = []

        for user in all_users:
            sid      = str(user.id)
            sessions = db.query(PracticeSession).filter(
                PracticeSession.student_id == sid,
                PracticeSession.status     == "completed"
            ).all()

            attempts = db.query(AssessmentAttempt).filter(
                AssessmentAttempt.student_id == sid
            ).all()

            mastered = db.query(AlphabetState).filter(
                AlphabetState.student_id == sid,
                AlphabetState.state      == "mastered"
            ).count()

            total_att = len(attempts)
            correct   = sum(1 for a in attempts if a.is_correct)
            accuracy  = round((correct / total_att) * 100, 2) if total_att else 0.0
            avg_conf  = round(
                sum(a.confidence for a in attempts) / total_att, 4
            ) if total_att else 0.0

            # Performance score
            score_result = scoring.calculate_performance_score(db, sid)
            perf_score   = score_result["data"]["final_score"]
            grade        = score_result["data"]["grade"]

            last_active = max(
                (s.start_time for s in sessions), default=None
            )

            student_data = {
                "student_id":      sid,
                "name":            user.full_name,
                "email":           user.email,
                "total_sessions":  len(sessions),
                "total_attempts":  total_att,
                "overall_accuracy":accuracy,
                "avg_confidence":  avg_conf,
                "letters_mastered":mastered,
                "performance_score": perf_score,
                "grade":           grade,
                "last_active":     last_active.isoformat() if last_active else None,
                "status": (
                    "at_risk"    if accuracy < 40 and total_att > 5
                    else "improving" if accuracy < 70
                    else "on_track"
                )
            }
            students.append(student_data)
            if total_att > 0:
                class_accs.append(accuracy)
                class_scores.append(perf_score)

        # Class-wide stats
        class_avg_accuracy = round(
            sum(class_accs) / len(class_accs), 2
        ) if class_accs else 0.0
        class_avg_score = round(
            sum(class_scores) / len(class_scores), 2
        ) if class_scores else 0.0

        at_risk    = [s for s in students if s["status"] == "at_risk"]
        top        = sorted(students, key=lambda x: x["performance_score"], reverse=True)[:5]
        struggling = sorted(students, key=lambda x: x["overall_accuracy"])[:5]

        return {
            "success": True,
            "data": {
                "generated_at":       datetime.utcnow().isoformat(),
                "total_students":     len(all_users),
                "class_avg_accuracy": class_avg_accuracy,
                "class_avg_score":    class_avg_score,
                "at_risk_count":      len(at_risk),
                "students":           students,
                "top_performers":     top,
                "struggling_students":struggling,
                "at_risk_students":   at_risk
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Per-student detail ─────────────────────────────────────────────────

    def get_student_detail(self, db: Session, student_id: str) -> dict:
        """Full breakdown for one student — for instructor drill-down."""
        sid  = str(student_id)
        user = db.query(User).filter(User.id == int(sid)).first()
        if not user:
            return {
                "success": False,
                "message": f"Student {sid} not found.",
                "data": None,
                "timestamp": datetime.utcnow().isoformat()
            }

        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == sid,
            PracticeSession.status     == "completed"
        ).order_by(PracticeSession.created_at.desc()).all()

        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.student_id == sid
        ).all()

        states = db.query(AlphabetState).filter(
            AlphabetState.student_id == sid
        ).all()

        metrics = db.query(ProgressMetrics).filter(
            ProgressMetrics.student_id == sid
        ).order_by(ProgressMetrics.session_number.asc()).all()

        # Per-letter accuracy
        letter_stats = defaultdict(lambda: {"correct": 0, "total": 0})
        for a in attempts:
            letter_stats[a.target_letter]["total"] += 1
            if a.is_correct:
                letter_stats[a.target_letter]["correct"] += 1

        letter_accuracy = {
            l: round((s["correct"] / s["total"]) * 100, 2)
            for l, s in letter_stats.items() if s["total"]
        }

        score_result = scoring.calculate_performance_score(db, sid)

        return {
            "success": True,
            "data": {
                "student_id":    sid,
                "name":          user.full_name,
                "email":         user.email,
                "performance":   score_result["data"],
                "total_sessions": len(sessions),
                "total_attempts": len(attempts),
                "letter_accuracy": letter_accuracy,
                "alphabet_states": {s.letter: s.state for s in states},
                "progress_trend": [
                    {
                        "session": m.session_number,
                        "accuracy": m.session_accuracy,
                        "delta":    m.accuracy_delta
                    }
                    for m in metrics
                ],
                "recent_sessions": [
                    {
                        "session_id":       s.session_id,
                        "date":             s.start_time.strftime("%Y-%m-%d %H:%M"),
                        "accuracy":         s.session_accuracy,
                        "attempts":         s.total_attempts,
                        "duration_seconds": s.total_duration_secs
                    }
                    for s in sessions[:10]
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Class progress tracking ────────────────────────────────────────────

    def get_class_progress(self, db: Session) -> dict:
        """Session-by-session class accuracy trend."""
        all_metrics = db.query(ProgressMetrics).order_by(
            ProgressMetrics.recorded_at.asc()
        ).all()

        # Group by date
        daily = defaultdict(list)
        for m in all_metrics:
            day = m.recorded_at.strftime("%Y-%m-%d")
            daily[day].append(m.session_accuracy)

        trend = [
            {
                "date":          day,
                "avg_accuracy":  round(sum(accs) / len(accs), 2),
                "session_count": len(accs)
            }
            for day, accs in sorted(daily.items())
        ]

        return {
            "success": True,
            "data": {
                "class_progress_trend": trend,
                "total_sessions_logged": len(all_metrics)
            },
            "timestamp": datetime.utcnow().isoformat()
        }