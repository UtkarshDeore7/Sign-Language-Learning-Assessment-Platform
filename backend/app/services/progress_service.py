"""
Progress Service
================
Cross-session progress tracking — answers the mentor's requirements:

  - Session-to-session accuracy & confidence improvement
  - Total learning progress percentage
  - Consecutive days practiced
  - Average attempts per alphabet
  - Alphabet-wise improvement trend
  - Progress Summary after every session:
      most improved / least improved / areas still needing practice
"""

import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import PracticeSession, AssessmentAttempt, ProgressMetrics, AlphabetState

logger = logging.getLogger(__name__)

MASTERED_THRESHOLD  = 85.0
IMPROVING_THRESHOLD = 50.0


class ProgressService:

    # ── Cross-session overview ─────────────────────────────────────────────

    def get_progress_overview(self, db: Session, student_id: str) -> dict:
        """
        Full cross-session progress view.
        Returns all sessions with per-session accuracy, delta, and trend.
        """
        metrics = db.query(ProgressMetrics).filter(
            ProgressMetrics.student_id == str(student_id)
        ).order_by(ProgressMetrics.session_number.asc()).all()

        if not metrics:
            return {
                "success": True,
                "message": "No completed sessions yet.",
                "data": {
                    "student_id":         student_id,
                    "total_sessions":     0,
                    "sessions":           [],
                    "overall_trend":      "no_data",
                    "consecutive_days":   0,
                    "total_progress_pct": 0.0
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        sessions_data = []
        for m in metrics:
            sessions_data.append({
                "session_number":       m.session_number,
                "session_id":           m.session_id,
                "session_accuracy":     m.session_accuracy,
                "prev_session_accuracy":m.prev_session_accuracy,
                "accuracy_delta":       m.accuracy_delta,
                "avg_confidence":       m.avg_confidence,
                "confidence_delta":     m.confidence_delta,
                "letters_practiced":    m.letters_practiced_count,
                "letters_mastered":     m.letters_mastered_count,
                "recorded_at":          m.recorded_at.isoformat()
            })

        # Overall trend direction
        if len(metrics) >= 2:
            recent   = metrics[-1].session_accuracy
            previous = metrics[-2].session_accuracy
            trend    = "improving" if recent > previous else \
                       "declining" if recent < previous else "stable"
        else:
            trend = "insufficient_data"

        # Consecutive days practiced
        consecutive_days = self._count_consecutive_days(db, student_id)

        # Total learning progress (% of 26 letters mastered)
        mastered_count = db.query(AlphabetState).filter(
            AlphabetState.student_id == str(student_id),
            AlphabetState.state      == "mastered"
        ).count()
        total_progress_pct = round((mastered_count / 26) * 100, 1)

        return {
            "success": True,
            "data": {
                "student_id":         student_id,
                "total_sessions":     len(metrics),
                "sessions":           sessions_data,
                "overall_trend":      trend,
                "consecutive_days":   consecutive_days,
                "total_progress_pct": total_progress_pct,
                "letters_mastered":   mastered_count
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Per-session progress summary ───────────────────────────────────────

    def get_session_progress_summary(
        self, db: Session, student_id: str, session_id: str
    ) -> dict:
        """
        Progress summary generated after a session completes.
        Highlights most improved, least improved, overall delta vs previous.
        """
        # Current session
        current = db.query(PracticeSession).filter(
            PracticeSession.session_id == session_id
        ).first()

        if not current:
            return {"success": False, "message": "Session not found.",
                    "data": None, "timestamp": datetime.utcnow().isoformat()}

        # Previous completed session for this student
        prev = db.query(PracticeSession).filter(
            PracticeSession.student_id == str(student_id),
            PracticeSession.status     == "completed",
            PracticeSession.session_id != session_id
        ).order_by(PracticeSession.created_at.desc()).first()

        acc_delta  = 0.0
        conf_delta = 0.0
        if prev:
            acc_delta  = round(current.session_accuracy - prev.session_accuracy, 2)
            conf_delta = round(current.avg_confidence   - prev.avg_confidence,   4)

        # Per-letter stats this session vs all-time
        this_attempts  = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.session_id == session_id
        ).all()

        letter_stats_this = defaultdict(lambda: {"correct": 0, "total": 0})
        for a in this_attempts:
            letter_stats_this[a.target_letter]["total"]  += 1
            if a.is_correct:
                letter_stats_this[a.target_letter]["correct"] += 1

        letter_acc_this = {
            l: round((s["correct"] / s["total"]) * 100, 2) if s["total"] else 0
            for l, s in letter_stats_this.items()
        }

        # Improvement vs previous session per letter
        letter_improvements = {}
        if prev:
            prev_attempts = db.query(AssessmentAttempt).filter(
                AssessmentAttempt.session_id == prev.session_id
            ).all()
            letter_stats_prev = defaultdict(lambda: {"correct": 0, "total": 0})
            for a in prev_attempts:
                letter_stats_prev[a.target_letter]["total"] += 1
                if a.is_correct:
                    letter_stats_prev[a.target_letter]["correct"] += 1

            for letter, stats in letter_stats_this.items():
                cur_acc  = letter_acc_this[letter]
                prev_acc = round(
                    (letter_stats_prev[letter]["correct"] /
                     letter_stats_prev[letter]["total"]) * 100, 2
                ) if letter_stats_prev[letter]["total"] else None

                if prev_acc is not None:
                    letter_improvements[letter] = {
                        "current": cur_acc,
                        "previous": prev_acc,
                        "delta": round(cur_acc - prev_acc, 2)
                    }

        most_improved  = None
        least_improved = None
        if letter_improvements:
            sorted_imp = sorted(
                letter_improvements.items(), key=lambda x: x[1]["delta"]
            )
            most_improved  = sorted_imp[-1][0] if sorted_imp[-1][1]["delta"] > 0 else None
            least_improved = sorted_imp[0][0]  if sorted_imp[0][1]["delta"]  < 0 else None

        # Areas still needing practice (accuracy < 70%)
        needs_practice = [
            {"letter": l, "accuracy": a}
            for l, a in sorted(letter_acc_this.items(), key=lambda x: x[1])
            if a < 70
        ]

        return {
            "success": True,
            "data": {
                "session_id":         session_id,
                "session_accuracy":   current.session_accuracy,
                "accuracy_vs_prev":   acc_delta,
                "confidence_vs_prev": conf_delta,
                "most_improved":      most_improved,
                "least_improved":     least_improved,
                "letter_accuracy":    letter_acc_this,
                "letter_improvements":letter_improvements,
                "needs_practice":     needs_practice,
                "overall_message":    self._progress_message(acc_delta)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Alphabet-wise trends ───────────────────────────────────────────────

    def get_alphabet_trends(self, db: Session, student_id: str) -> dict:
        """
        Per-letter trend across all sessions.
        Shows how accuracy evolved over time for each letter.
        """
        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == str(student_id),
            PracticeSession.status     == "completed"
        ).order_by(PracticeSession.created_at.asc()).all()

        if not sessions:
            return {"success": True, "data": {"trends": {}},
                    "timestamp": datetime.utcnow().isoformat()}

        letter_trends: dict = defaultdict(list)

        for s in sessions:
            attempts = db.query(AssessmentAttempt).filter(
                AssessmentAttempt.session_id == s.session_id
            ).all()
            stats = defaultdict(lambda: {"correct": 0, "total": 0})
            for a in attempts:
                stats[a.target_letter]["total"] += 1
                if a.is_correct:
                    stats[a.target_letter]["correct"] += 1

            for letter, st in stats.items():
                acc = round((st["correct"] / st["total"]) * 100, 2) if st["total"] else 0
                letter_trends[letter].append({
                    "session_number": len(letter_trends[letter]) + 1,
                    "accuracy":       acc,
                    "date":           s.start_time.strftime("%Y-%m-%d")
                })

        # Average attempts per alphabet
        avg_attempts = {}
        for letter, trend_list in letter_trends.items():
            total_attempts = sum(
                db.query(func.count(AssessmentAttempt.id)).filter(
                    AssessmentAttempt.student_id    == str(student_id),
                    AssessmentAttempt.target_letter == letter
                ).scalar() or 0
                for _ in [1]
            )
            avg_attempts[letter] = round(
                total_attempts / len(sessions), 1
            )

        return {
            "success": True,
            "data": {
                "student_id":    student_id,
                "total_sessions": len(sessions),
                "trends":         dict(letter_trends),
                "avg_attempts_per_letter": avg_attempts
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Helpers ────────────────────────────────────────────────────────────

    def _count_consecutive_days(self, db: Session, student_id: str) -> int:
        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == str(student_id),
            PracticeSession.status     == "completed"
        ).order_by(PracticeSession.start_time.desc()).all()

        if not sessions:
            return 0

        practiced_dates = sorted(
            set(s.start_time.date() for s in sessions), reverse=True
        )

        count    = 1
        today    = datetime.utcnow().date()
        expected = practiced_dates[0]

        if expected < today - timedelta(days=1):
            return 0  # broke the streak

        for i in range(1, len(practiced_dates)):
            if practiced_dates[i] == expected - timedelta(days=1):
                count    += 1
                expected  = practiced_dates[i]
            else:
                break
        return count

    def _progress_message(self, delta: float) -> str:
        if delta > 10:
            return "Excellent improvement this session! 🎉"
        elif delta > 5:
            return "Good progress — keep it up! 👍"
        elif delta > 0:
            return "Small improvement — consistency will get you there."
        elif delta == 0:
            return "Same as last session — try focusing on weaker letters."
        else:
            return "Slight dip — don't worry, review your weak letters."