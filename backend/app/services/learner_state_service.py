"""
Learner State Service
=====================
Implements a state machine per (student_id, letter).

States
------
not_attempted  — letter has never been attempted
learning       — attempts started, accuracy still low
improving      — consistent progress, crossing 50%
mastered       — high accuracy + high confidence sustained
needs_revision — was mastered but recently declining

Transition Rules (evaluated after every attempt)
-------------------------------------------------
not_attempted  → learning       : first attempt made
learning       → improving      : accuracy >= 50%  over last 5  attempts
improving      → mastered       : accuracy >= 85%  AND
                                  avg_confidence >= 0.75
                                  over last 10 attempts
mastered       → needs_revision : 3+ consecutive incorrect
needs_revision → improving      : accuracy >= 60%  over last 5  attempts
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import AlphabetState, AlphabetStateHistory, AssessmentAttempt

logger = logging.getLogger(__name__)

# ── State constants ────────────────────────────────────────────────────────────
NOT_ATTEMPTED  = "not_attempted"
LEARNING       = "learning"
IMPROVING      = "improving"
MASTERED       = "mastered"
NEEDS_REVISION = "needs_revision"

# ── Transition thresholds ──────────────────────────────────────────────────────
LEARNING_TO_IMPROVING_ACC    = 50.0   # % accuracy over last 5 attempts
IMPROVING_TO_MASTERED_ACC    = 85.0   # % accuracy over last 10 attempts
IMPROVING_TO_MASTERED_CONF   = 0.75   # avg confidence over last 10 attempts
MASTERED_TO_REVISION_STREAK  = 3      # consecutive incorrect → needs revision
REVISION_TO_IMPROVING_ACC    = 60.0   # % accuracy over last 5 attempts
WINDOW_SHORT = 5
WINDOW_LONG  = 10


class LearnerStateService:

    # ── Public: update after every attempt ────────────────────────────────────

    def update_state(
        self,
        db:         Session,
        student_id: str,
        letter:     str,
        is_correct: bool,
        confidence: float
    ) -> dict:
        """
        Called after every attempt on `letter`.
        Updates running stats and evaluates whether a state transition
        should occur. Persists everything to DB.
        """
        letter = letter.upper()

        # Get or create state row
        state_row = db.query(AlphabetState).filter(
            AlphabetState.student_id == str(student_id),
            AlphabetState.letter     == letter
        ).first()

        if not state_row:
            state_row = AlphabetState(
                student_id           = str(student_id),
                letter               = letter,
                state                = NOT_ATTEMPTED,
                total_attempts       = 0,
                correct_attempts     = 0,
                accuracy             = 0.0,
                avg_confidence       = 0.0,
                consecutive_correct  = 0,
                consecutive_incorrect= 0,
                confused_with        = "{}",
                state_history        = "[]",
                state_changed_at     = datetime.utcnow()
            )
            db.add(state_row)
            db.flush()   # get id without committing

        # ── Update running stats ──────────────────────────────────────────
        state_row.total_attempts   += 1
        state_row.last_practiced    = datetime.utcnow()

        if is_correct:
            state_row.correct_attempts    += 1
            state_row.consecutive_correct += 1
            state_row.consecutive_incorrect = 0
        else:
            state_row.consecutive_incorrect += 1
            state_row.consecutive_correct    = 0

        state_row.accuracy = round(
            (state_row.correct_attempts / state_row.total_attempts) * 100, 2
        )

        # Rolling average confidence
        n = state_row.total_attempts
        state_row.avg_confidence = round(
            ((state_row.avg_confidence * (n - 1)) + confidence) / n, 4
        )

        # ── Evaluate transition ───────────────────────────────────────────
        old_state = state_row.state
        new_state = self._evaluate_transition(db, state_row)

        if new_state != old_state:
            self._apply_transition(db, state_row, old_state, new_state)

        db.commit()
        db.refresh(state_row)

        return {
            "letter":                letter,
            "state":                 state_row.state,
            "previous_state":        old_state,
            "transitioned":          new_state != old_state,
            "accuracy":              state_row.accuracy,
            "avg_confidence":        state_row.avg_confidence,
            "total_attempts":        state_row.total_attempts,
            "consecutive_correct":   state_row.consecutive_correct,
            "consecutive_incorrect": state_row.consecutive_incorrect
        }

    # ── Public: read state(s) ─────────────────────────────────────────────────

    def get_state(self, db: Session, student_id: str, letter: str) -> dict:
        letter    = letter.upper()
        state_row = db.query(AlphabetState).filter(
            AlphabetState.student_id == str(student_id),
            AlphabetState.letter     == letter
        ).first()

        if not state_row:
            return {
                "success": True,
                "data": {
                    "letter": letter,
                    "state":  NOT_ATTEMPTED,
                    "accuracy": 0.0,
                    "avg_confidence": 0.0,
                    "total_attempts": 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        return {
            "success": True,
            "data":    self._serialize(state_row),
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_all_states(self, db: Session, student_id: str) -> dict:
        """
        Returns state for all 26 letters.
        Letters not yet attempted are included as not_attempted.
        """
        rows = db.query(AlphabetState).filter(
            AlphabetState.student_id == str(student_id)
        ).all()

        state_map = {r.letter: self._serialize(r) for r in rows}

        # Fill in letters that have never been attempted
        all_states = {}
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter in state_map:
                all_states[letter] = state_map[letter]
            else:
                all_states[letter] = {
                    "letter":                letter,
                    "state":                 NOT_ATTEMPTED,
                    "accuracy":              0.0,
                    "avg_confidence":        0.0,
                    "total_attempts":        0,
                    "correct_attempts":      0,
                    "consecutive_correct":   0,
                    "consecutive_incorrect": 0,
                    "last_practiced":        None,
                    "state_changed_at":      None
                }

        # Dashboard summary counts
        counts = {
            NOT_ATTEMPTED:  0,
            LEARNING:       0,
            IMPROVING:      0,
            MASTERED:       0,
            NEEDS_REVISION: 0
        }
        for s in all_states.values():
            counts[s["state"]] += 1

        mastery_pct = round((counts[MASTERED] / 26) * 100, 1)

        return {
            "success": True,
            "data": {
                "student_id":   student_id,
                "alphabet_states": all_states,
                "summary": {
                    "not_attempted":  counts[NOT_ATTEMPTED],
                    "learning":       counts[LEARNING],
                    "improving":      counts[IMPROVING],
                    "mastered":       counts[MASTERED],
                    "needs_revision": counts[NEEDS_REVISION],
                    "mastery_percent": mastery_pct
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_state_history(self, db: Session, student_id: str, letter: str) -> dict:
        """Full transition history for one letter."""
        letter = letter.upper()
        history = db.query(AlphabetStateHistory).filter(
            AlphabetStateHistory.student_id == str(student_id),
            AlphabetStateHistory.letter     == letter
        ).order_by(AlphabetStateHistory.transitioned_at.asc()).all()

        return {
            "success": True,
            "data": {
                "letter": letter,
                "transitions": [
                    {
                        "from_state":      h.from_state,
                        "to_state":        h.to_state,
                        "reason":          h.reason,
                        "transitioned_at": h.transitioned_at.isoformat()
                    }
                    for h in history
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Recommendation using state ─────────────────────────────────────────────

    def get_recommendations(self, db: Session, student_id: str) -> dict:
        """
        Generate a prioritised practice queue using learner state.
        Priority: needs_revision > learning > improving (low conf) > not_attempted
        mastered letters are excluded unless confidence is low.
        """
        rows = db.query(AlphabetState).filter(
            AlphabetState.student_id == str(student_id)
        ).all()
        state_map = {r.letter: r for r in rows}

        recommendations = []

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in state_map:
                recommendations.append({
                    "letter":   letter,
                    "state":    NOT_ATTEMPTED,
                    "reason":   "Not practiced yet — start here",
                    "priority": "medium"
                })
                continue

            r = state_map[letter]

            if r.state == NEEDS_REVISION:
                confused = json.loads(r.confused_with or "{}")
                top = max(confused, key=confused.get) if confused else None
                reason = f"Was mastered but recently declining"
                if top:
                    reason += f" — often confused with '{top}'"
                recommendations.append({
                    "letter": letter, "state": r.state,
                    "accuracy": r.accuracy, "reason": reason,
                    "priority": "high"
                })

            elif r.state == LEARNING:
                recommendations.append({
                    "letter": letter, "state": r.state,
                    "accuracy": r.accuracy,
                    "reason": f"Still learning — accuracy {r.accuracy}%",
                    "priority": "high"
                })

            elif r.state == IMPROVING and r.avg_confidence < 0.70:
                recommendations.append({
                    "letter": letter, "state": r.state,
                    "accuracy": r.accuracy,
                    "reason": f"Improving but confidence low ({r.avg_confidence:.0%})",
                    "priority": "medium"
                })

            elif r.state == NOT_ATTEMPTED:
                recommendations.append({
                    "letter": letter, "state": r.state,
                    "reason": "Not practiced yet",
                    "priority": "medium"
                })

            elif r.state == MASTERED:
                recommendations.append({
                    "letter": letter, "state": r.state,
                    "accuracy": r.accuracy,
                    "reason": "Mastered — keep it sharp",
                    "priority": "low"
                })

            else:  # improving, decent confidence
                recommendations.append({
                    "letter": letter, "state": r.state,
                    "accuracy": r.accuracy,
                    "reason": f"Good progress — keep going",
                    "priority": "medium"
                })

        # Sort: high → medium → low, then by accuracy asc within group
        order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: (order[x["priority"]], x.get("accuracy", 0)))

        return {
            "success": True,
            "data": {
                "recommended_queue": recommendations[:10],
                "next_letter":       recommendations[0]["letter"] if recommendations else "A",
                "total":             len(recommendations)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Internal: transition logic ─────────────────────────────────────────────

    def _evaluate_transition(self, db: Session, row: AlphabetState) -> str:
        current = row.state

        # Pull recent attempts for this (student, letter) from DB
        recent_all = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.student_id    == row.student_id,
            AssessmentAttempt.target_letter == row.letter
        ).order_by(AssessmentAttempt.timestamp.desc()).limit(WINDOW_LONG).all()

        recent_5  = recent_all[:WINDOW_SHORT]
        recent_10 = recent_all[:WINDOW_LONG]

        def acc(attempts):
            if not attempts:
                return 0.0
            return (sum(1 for a in attempts if a.is_correct) / len(attempts)) * 100

        def avg_conf(attempts):
            if not attempts:
                return 0.0
            return sum(a.confidence for a in attempts) / len(attempts)

        # ── Transition rules ──────────────────────────────────────────────
        if current == NOT_ATTEMPTED:
            # First attempt always moves to learning
            if row.total_attempts >= 1:
                return LEARNING

        elif current == LEARNING:
            if len(recent_5) >= WINDOW_SHORT and acc(recent_5) >= LEARNING_TO_IMPROVING_ACC:
                return IMPROVING

        elif current == IMPROVING:
            if (len(recent_10) >= WINDOW_LONG
                    and acc(recent_10)      >= IMPROVING_TO_MASTERED_ACC
                    and avg_conf(recent_10) >= IMPROVING_TO_MASTERED_CONF):
                return MASTERED

        elif current == MASTERED:
            if row.consecutive_incorrect >= MASTERED_TO_REVISION_STREAK:
                return NEEDS_REVISION

        elif current == NEEDS_REVISION:
            if len(recent_5) >= WINDOW_SHORT and acc(recent_5) >= REVISION_TO_IMPROVING_ACC:
                return IMPROVING

        return current   # no transition

    def _apply_transition(
        self, db: Session, row: AlphabetState,
        from_state: str, to_state: str
    ):
        reason = self._transition_reason(from_state, to_state, row)

        # Update state row
        row.state            = to_state
        row.state_changed_at = datetime.utcnow()

        # Append to inline history
        history = json.loads(row.state_history or "[]")
        history.append({
            "from": from_state, "to": to_state,
            "reason": reason,
            "at": datetime.utcnow().isoformat()
        })
        row.state_history = json.dumps(history)

        # Write to audit table
        log = AlphabetStateHistory(
            alphabet_state_id = row.id,
            student_id        = row.student_id,
            letter            = row.letter,
            from_state        = from_state,
            to_state          = to_state,
            reason            = reason,
            transitioned_at   = datetime.utcnow()
        )
        db.add(log)

        logger.info(
            f"State transition | student={row.student_id} letter={row.letter} "
            f"{from_state} → {to_state} | {reason}"
        )

    def _transition_reason(self, from_s: str, to_s: str, row: AlphabetState) -> str:
        if from_s == NOT_ATTEMPTED and to_s == LEARNING:
            return "First attempt recorded"
        if from_s == LEARNING and to_s == IMPROVING:
            return f"Accuracy crossed 50% over last {WINDOW_SHORT} attempts"
        if from_s == IMPROVING and to_s == MASTERED:
            return (f"Accuracy ≥ 85% and confidence ≥ 75% "
                    f"over last {WINDOW_LONG} attempts")
        if from_s == MASTERED and to_s == NEEDS_REVISION:
            return f"{row.consecutive_incorrect} consecutive incorrect answers"
        if from_s == NEEDS_REVISION and to_s == IMPROVING:
            return f"Accuracy recovered above 60% over last {WINDOW_SHORT} attempts"
        return f"{from_s} → {to_s}"

    # ── Serializer ────────────────────────────────────────────────────────────

    def _serialize(self, row: AlphabetState) -> dict:
        return {
            "letter":                row.letter,
            "state":                 row.state,
            "accuracy":              row.accuracy,
            "avg_confidence":        row.avg_confidence,
            "total_attempts":        row.total_attempts,
            "correct_attempts":      row.correct_attempts,
            "consecutive_correct":   row.consecutive_correct,
            "consecutive_incorrect": row.consecutive_incorrect,
            "last_practiced":        row.last_practiced.isoformat() if row.last_practiced else None,
            "state_changed_at":      row.state_changed_at.isoformat() if row.state_changed_at else None
        }