"""
Admin Service
=============
Powers the Admin Dashboard:
  - Platform-wide statistics
  - User management
  - System health
  - Content analytics
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    User, Role, LearnerProfile,
    PracticeSession, AssessmentAttempt,
    AlphabetState, Certificate, Badge
)

logger = logging.getLogger(__name__)


class AdminService:

    # ── Platform overview ──────────────────────────────────────────────────

    def get_platform_overview(self, db: Session) -> dict:
        """Complete platform stats for the admin dashboard."""

        # Users
        total_users   = db.query(User).count()
        active_users  = db.query(User).filter(User.is_active == True).count()

        # Sessions
        total_sessions    = db.query(PracticeSession).count()
        completed_sessions = db.query(PracticeSession).filter(
            PracticeSession.status == "completed"
        ).count()
        active_sessions   = db.query(PracticeSession).filter(
            PracticeSession.status == "active"
        ).count()

        # Attempts
        total_attempts = db.query(AssessmentAttempt).count()
        total_correct  = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.is_correct == True
        ).count()
        platform_accuracy = round(
            (total_correct / total_attempts) * 100, 2
        ) if total_attempts else 0.0

        avg_confidence = db.query(
            func.avg(AssessmentAttempt.confidence)
        ).scalar() or 0.0
        avg_inference  = db.query(
            func.avg(AssessmentAttempt.inference_time_ms)
        ).scalar() or 0.0

        # Certificates and badges
        total_certs  = db.query(Certificate).count()
        total_badges = db.query(Badge).count()

        # Most practiced letters across platform
        letter_counts = db.query(
            AssessmentAttempt.target_letter,
            func.count(AssessmentAttempt.id).label("count")
        ).group_by(
            AssessmentAttempt.target_letter
        ).order_by(func.count(AssessmentAttempt.id).desc()).limit(5).all()

        # Activity last 7 days
        week_ago    = datetime.utcnow() - timedelta(days=7)
        daily_usage = defaultdict(int)
        recent_sessions = db.query(PracticeSession).filter(
            PracticeSession.created_at >= week_ago
        ).all()
        for s in recent_sessions:
            day = s.created_at.strftime("%Y-%m-%d")
            daily_usage[day] += 1

        activity_trend = [
            {"date": day, "sessions": count}
            for day, count in sorted(daily_usage.items())
        ]

        return {
            "success": True,
            "data": {
                "generated_at": datetime.utcnow().isoformat(),

                # Users
                "total_users":    total_users,
                "active_users":   active_users,
                "inactive_users": total_users - active_users,

                # Sessions
                "total_sessions":     total_sessions,
                "completed_sessions": completed_sessions,
                "active_sessions":    active_sessions,

                # Performance
                "total_attempts":     total_attempts,
                "platform_accuracy":  platform_accuracy,
                "avg_confidence":     round(float(avg_confidence) * 100, 2),
                "avg_inference_ms":   round(float(avg_inference), 2),

                # Achievements
                "total_certificates": total_certs,
                "total_badges":       total_badges,

                # Content analytics
                "most_practiced_letters": [
                    {"letter": r.target_letter, "count": r.count}
                    for r in letter_counts
                ],

                # Activity
                "activity_last_7_days": activity_trend
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── User management ────────────────────────────────────────────────────

    def get_all_users(self, db: Session) -> dict:
        """List all users with their roles and basic stats."""
        users = db.query(User).all()
        roles = {r.id: r.name for r in db.query(Role).all()}

        result = []
        for u in users:
            sessions = db.query(PracticeSession).filter(
                PracticeSession.student_id == str(u.id),
                PracticeSession.status     == "completed"
            ).count()

            result.append({
                "id":           u.id,
                "name":         u.full_name,
                "email":        u.email,
                "role":         roles.get(u.role_id, "learner"),
                "is_active":    u.is_active,
                "joined":       u.created_at.strftime("%Y-%m-%d"),
                "total_sessions": sessions
            })

        return {
            "success": True,
            "data": {
                "total": len(result),
                "users": result
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def toggle_user_status(self, db: Session, user_id: int) -> dict:
        """Activate or deactivate a user."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "message": f"User {user_id} not found.",
                "data": None,
                "timestamp": datetime.utcnow().isoformat()
            }

        user.is_active = not user.is_active
        db.commit()

        return {
            "success": True,
            "message": f"User {'activated' if user.is_active else 'deactivated'}.",
            "data": {"user_id": user_id, "is_active": user.is_active},
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── System health ──────────────────────────────────────────────────────

    def get_system_health(self, db: Session) -> dict:
        """Basic system health check."""
        try:
            db.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {e}"

        return {
            "success": True,
            "data": {
                "status":      "operational",
                "database":    db_status,
                "api":         "healthy",
                "checked_at":  datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Seed roles ─────────────────────────────────────────────────────────

    def seed_roles(self, db: Session) -> dict:
        """
        Ensure the 4 roles exist in the DB.
        Safe to call multiple times — skips existing roles.
        """
        roles = ["learner", "instructor", "accessibility_trainer", "administrator"]
        created = []

        for name in roles:
            existing = db.query(Role).filter(Role.name == name).first()
            if not existing:
                db.add(Role(name=name))
                created.append(name)

        db.commit()

        return {
            "success": True,
            "data": {
                "created": created,
                "message": "Roles seeded successfully."
            },
            "timestamp": datetime.utcnow().isoformat()
        }