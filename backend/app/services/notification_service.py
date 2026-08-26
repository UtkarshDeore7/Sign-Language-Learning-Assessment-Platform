"""
Notification Service
====================
Event-driven notifications stored in DB.

Events that trigger notifications:
  - session_completed  → practice session ended
  - badge_earned       → milestone badge awarded
  - cert_issued        → certificate generated
  - milestone          → specific progress milestone hit
  - reminder           → practice reminder (manual trigger)
"""

import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from models import Notification

logger = logging.getLogger(__name__)


class NotificationService:

    # ── Create ─────────────────────────────────────────────────────────────

    def notify(
        self,
        db: Session,
        student_id: str,
        type: str,
        title: str,
        message: str,
        data: dict = None
    ) -> dict:
        n = Notification(
            student_id = str(student_id),
            type       = type,
            title      = title,
            message    = message,
            data       = json.dumps(data) if data else None,
            is_read    = False,
            created_at = datetime.utcnow()
        )
        db.add(n)
        db.commit()
        db.refresh(n)
        logger.info(f"Notification | {type} | student={student_id} | {title}")
        return self._serialize(n)

    # ── Event helpers (called by other services) ───────────────────────────

    def on_session_completed(self, db, student_id, accuracy, attempts):
        self.notify(db, student_id,
            type    = "session_completed",
            title   = "Practice Session Complete",
            message = f"You finished a session with {accuracy}% accuracy over {attempts} attempts.",
            data    = {"accuracy": accuracy, "attempts": attempts}
        )

    def on_badge_earned(self, db, student_id, badge_id, badge_name, icon):
        self.notify(db, student_id,
            type    = "badge_earned",
            title   = f"{icon} Badge Earned: {badge_name}",
            message = f"You just earned the '{badge_name}' badge. Keep it up!",
            data    = {"badge_id": badge_id}
        )

    def on_cert_issued(self, db, student_id, score, grade):
        self.notify(db, student_id,
            type    = "cert_issued",
            title   = "🎓 Certificate Issued!",
            message = f"Congratulations! You earned your ASL certificate with a score of {score}% (Grade: {grade}).",
            data    = {"score": score, "grade": grade}
        )

    def on_milestone(self, db, student_id, milestone_text):
        self.notify(db, student_id,
            type    = "milestone",
            title   = "🏆 Milestone Reached",
            message = milestone_text
        )

    # ── Read ───────────────────────────────────────────────────────────────

    def get_notifications(self, db: Session, student_id: str, unread_only: bool = False) -> dict:
        q = db.query(Notification).filter(
            Notification.student_id == str(student_id)
        )
        if unread_only:
            q = q.filter(Notification.is_read == False)
        notifications = q.order_by(Notification.created_at.desc()).limit(20).all()

        unread_count = db.query(Notification).filter(
            Notification.student_id == str(student_id),
            Notification.is_read    == False
        ).count()

        return {
            "success": True,
            "data": {
                "student_id":    student_id,
                "unread_count":  unread_count,
                "notifications": [self._serialize(n) for n in notifications]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def mark_read(self, db: Session, student_id: str, notification_id: int) -> dict:
        n = db.query(Notification).filter(
            Notification.id         == notification_id,
            Notification.student_id == str(student_id)
        ).first()
        if not n:
            return {"success": False, "message": "Notification not found.",
                    "data": None, "timestamp": datetime.utcnow().isoformat()}
        n.is_read = True
        db.commit()
        return {"success": True, "message": "Marked as read.",
                "data": {"id": notification_id}, "timestamp": datetime.utcnow().isoformat()}

    def mark_all_read(self, db: Session, student_id: str) -> dict:
        db.query(Notification).filter(
            Notification.student_id == str(student_id),
            Notification.is_read    == False
        ).update({"is_read": True})
        db.commit()
        return {"success": True, "message": "All marked as read.",
                "data": None, "timestamp": datetime.utcnow().isoformat()}

    # ── Helper ─────────────────────────────────────────────────────────────

    def _serialize(self, n: Notification) -> dict:
        return {
            "id":         n.id,
            "type":       n.type,
            "title":      n.title,
            "message":    n.message,
            "is_read":    n.is_read,
            "data":       json.loads(n.data) if n.data else None,
            "created_at": n.created_at.isoformat()
        }