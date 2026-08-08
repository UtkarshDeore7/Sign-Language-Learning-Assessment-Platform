"""
Analytics Service
=================
Real-time aggregation of all learner stats from the DB.
Called by the dashboard endpoint and after every assessment.
No hardcoded values — everything derived from DB records.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    PracticeSession, AssessmentAttempt,
    AlphabetState, ProgressMetrics, SessionSummary
)

logger = logging.getLogger(__name__)


class AnalyticsService:

    def get_dashboard(self, db: Session, student_id: str) -> dict:
        """
        Single call that returns everything the dashboard needs.
        Recalculated live from DB on every call — no caching.
        """
        sid = str(student_id)

        # ── Sessions ──────────────────────────────────────────────────────
        all_sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == sid,
            PracticeSession.status     == "completed"
        ).order_by(PracticeSession.created_at.desc()).all()

        active_session = db.query(PracticeSession).filter(
            PracticeSession.student_id == sid,
            PracticeSession.status     == "active"
        ).order_by(PracticeSession.created_at.desc()).first()

        # ── Attempts ──────────────────────────────────────────────────────
        all_attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.student_id == sid
        ).all()

        total_attempts = len(all_attempts)
        total_correct  = sum(1 for a in all_attempts if a.is_correct)
        overall_acc    = round((total_correct / total_attempts) * 100, 2) if total_attempts else 0.0
        avg_conf       = round(sum(a.confidence for a in all_attempts) / total_attempts, 4) if total_attempts else 0.0
        avg_inf        = round(sum(a.inference_time_ms for a in all_attempts) / total_attempts, 2) if total_attempts else 0.0

        # ── Alphabet states ───────────────────────────────────────────────
        states = db.query(AlphabetState).filter(
            AlphabetState.student_id == sid
        ).all()

        state_counts = defaultdict(int)
        for s in states:
            state_counts[s.state] += 1

        mastered_count = state_counts.get("mastered", 0)
        mastery_pct    = round((mastered_count / 26) * 100, 1)

        # ── Per-letter stats ──────────────────────────────────────────────
        letter_stats   = defaultdict(lambda: {"correct": 0, "total": 0})
        confusion_map  = defaultdict(lambda: defaultdict(int))
        freq_map       = defaultdict(int)

        for a in all_attempts:
            letter_stats[a.target_letter]["total"] += 1
            freq_map[a.target_letter]             += 1
            if a.is_correct:
                letter_stats[a.target_letter]["correct"] += 1
            else:
                confusion_map[a.target_letter][a.predicted_letter] += 1

        letter_accuracy = {
            l: round((s["correct"] / s["total"]) * 100, 2) if s["total"] else 0
            for l, s in letter_stats.items()
        }

        sorted_acc    = sorted(letter_accuracy.items(), key=lambda x: x[1])
        strongest     = [l for l, _ in sorted_acc[-3:][::-1]] if sorted_acc else []
        weakest       = [l for l, _ in sorted_acc[:3]]         if sorted_acc else []
        most_practiced = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)[:5]

        # ── Progress trend (last 5 sessions) ─────────────────────────────
        metrics = db.query(ProgressMetrics).filter(
            ProgressMetrics.student_id == sid
        ).order_by(ProgressMetrics.session_number.desc()).limit(5).all()

        trend = [
            {
                "session_number": m.session_number,
                "accuracy":       m.session_accuracy,
                "delta":          m.accuracy_delta,
                "confidence":     m.avg_confidence
            }
            for m in reversed(metrics)
        ]

        # Consecutive days
        consecutive_days = self._consecutive_days(db, sid)

        # ── Current / last session stats ──────────────────────────────────
        current_session_data = None
        if active_session:
            current_session_data = {
                "session_id":      active_session.session_id,
                "status":          "active",
                "total_attempts":  active_session.total_attempts,
                "session_accuracy":active_session.session_accuracy,
                "avg_confidence":  active_session.avg_confidence,
                "correct":         active_session.correct_attempts,
                "incorrect":       active_session.incorrect_attempts
            }
        elif all_sessions:
            s = all_sessions[0]
            current_session_data = {
                "session_id":      s.session_id,
                "status":          "completed",
                "total_attempts":  s.total_attempts,
                "session_accuracy":s.session_accuracy,
                "avg_confidence":  s.avg_confidence,
                "correct":         s.correct_attempts,
                "incorrect":       s.incorrect_attempts
            }

        return {
            "success": True,
            "data": {
                "student_id":         sid,
                "generated_at":       datetime.utcnow().isoformat(),

                # Overview
                "total_sessions":     len(all_sessions),
                "total_attempts":     total_attempts,
                "overall_accuracy":   overall_acc,
                "avg_confidence":     avg_conf,
                "avg_inference_ms":   avg_inf,
                "consecutive_days":   consecutive_days,

                # Mastery
                "mastery_percent":    mastery_pct,
                "letters_mastered":   mastered_count,
                "state_counts": {
                    "not_attempted":  state_counts.get("not_attempted",  26 - len(states)),
                    "learning":       state_counts.get("learning",        0),
                    "improving":      state_counts.get("improving",       0),
                    "mastered":       state_counts.get("mastered",        0),
                    "needs_revision": state_counts.get("needs_revision",  0)
                },

                # Letter performance
                "strongest_letters":  strongest,
                "weakest_letters":    weakest,
                "most_practiced":     [{"letter": l, "count": c} for l, c in most_practiced],
                "letter_accuracy":    letter_accuracy,

                # Progress trend
                "progress_trend":     trend,
                "total_improvement":  round(trend[-1]["accuracy"] - trend[0]["accuracy"], 2)
                                      if len(trend) >= 2 else 0.0,

                # Current session
                "current_session":    current_session_data,

                # Recent sessions
                "recent_sessions": [
                    {
                        "session_id":       s.session_id,
                        "session_accuracy": s.session_accuracy,
                        "total_attempts":   s.total_attempts,
                        "date":             s.start_time.strftime("%Y-%m-%d %H:%M")
                    }
                    for s in all_sessions[:5]
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def update_learner_profile(self, db: Session, student_id: str):
        """
        Called after every assessment attempt.
        Updates the LearnerProfile row with current analytics.
        """
        from models import LearnerProfile, User
        from sqlalchemy import cast, Integer

        try:
            # Try to find user by student_id (could be int id or string)
            user = None
            try:
                user = db.query(User).filter(
                    User.id == int(student_id)
                ).first()
            except (ValueError, TypeError):
                pass

            if not user:
                return  # student_id not a registered user — skip profile update

            profile = db.query(LearnerProfile).filter(
                LearnerProfile.user_id == user.id
            ).first()

            if not profile:
                return  # no profile row yet

            # Get current stats
            attempts = db.query(AssessmentAttempt).filter(
                AssessmentAttempt.student_id == student_id
            ).all()

            if not attempts:
                return

            total    = len(attempts)
            correct  = sum(1 for a in attempts if a.is_correct)
            accuracy = round((correct / total) * 100, 2)

            # Get mastery state
            states = db.query(AlphabetState).filter(
                AlphabetState.student_id == student_id
            ).all()
            mastered = sum(1 for s in states if s.state == "mastered")

            # Update profile fields
            profile.practice_statistics = json.dumps({
                "total_attempts": total,
                "overall_accuracy": accuracy,
                "letters_mastered": mastered,
                "mastery_percent": round((mastered / 26) * 100, 1),
                "last_updated": datetime.utcnow().isoformat()
            })

            db.commit()

        except Exception as e:
            logger.warning(f"Profile update skipped: {e}")

    def _consecutive_days(self, db: Session, student_id: str) -> int:
        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == student_id,
            PracticeSession.status     == "completed"
        ).order_by(PracticeSession.start_time.desc()).all()

        if not sessions:
            return 0

        dates    = sorted(set(s.start_time.date() for s in sessions), reverse=True)
        today    = datetime.utcnow().date()
        expected = dates[0]

        if expected < today - timedelta(days=1):
            return 0

        count = 1
        for i in range(1, len(dates)):
            if dates[i] == expected - timedelta(days=1):
                count   += 1
                expected = dates[i]
            else:
                break
        return count