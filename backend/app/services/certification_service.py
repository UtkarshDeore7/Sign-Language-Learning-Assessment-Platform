"""
Certification Service
=====================
Handles:
  1. Eligibility check (based on weighted performance score)
  2. Badge award system (auto-awarded based on milestones)
  3. PDF certificate generation using reportlab

Badge milestones:
  first_session      — completed first practice session
  five_sessions      — completed 5 sessions
  ten_sessions       — completed 10 sessions
  first_mastery      — first letter mastered
  ten_mastery        — 10 letters mastered
  full_alphabet      — all 26 letters mastered
  streak_3           — 3 consecutive days practiced
  streak_7           — 7 consecutive days practiced
  high_accuracy      — session accuracy >= 90%
  certified          — performance score >= 70
"""

import io
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from models import (
    Certificate, Badge,
    PracticeSession, AlphabetState, ProgressMetrics
)
from services.scoring_service import ScoringService

logger = logging.getLogger(__name__)
_scoring = ScoringService()

# ── Badge definitions ──────────────────────────────────────────────────────
BADGE_DEFS = [
    {
        "id":          "first_session",
        "name":        "First Step",
        "description": "Completed your first practice session",
        "icon":        "🎯"
    },
    {
        "id":          "five_sessions",
        "name":        "Consistent Learner",
        "description": "Completed 5 practice sessions",
        "icon":        "🔥"
    },
    {
        "id":          "ten_sessions",
        "name":        "Dedicated Practitioner",
        "description": "Completed 10 practice sessions",
        "icon":        "⭐"
    },
    {
        "id":          "first_mastery",
        "name":        "First Master",
        "description": "Mastered your first letter",
        "icon":        "🏆"
    },
    {
        "id":          "ten_mastery",
        "name":        "Sign Expert",
        "description": "Mastered 10 letters",
        "icon":        "💎"
    },
    {
        "id":          "full_alphabet",
        "name":        "ASL Champion",
        "description": "Mastered all 26 letters",
        "icon":        "🥇"
    },
    {
        "id":          "streak_3",
        "name":        "3-Day Streak",
        "description": "Practiced 3 days in a row",
        "icon":        "📅"
    },
    {
        "id":          "streak_7",
        "name":        "Weekly Warrior",
        "description": "Practiced 7 days in a row",
        "icon":        "🗓️"
    },
    {
        "id":          "high_accuracy",
        "name":        "Sharp Eye",
        "description": "Achieved 90%+ accuracy in a session",
        "icon":        "🎯"
    },
    {
        "id":          "certified",
        "name":        "ASL Certified",
        "description": "Earned ASL Learning Certificate",
        "icon":        "📜"
    },
]


class CertificationService:

    # ── Eligibility ───────────────────────────────────────────────────────

    def check_eligibility(self, db: Session, student_id: str) -> dict:
        """
        Check if student is eligible for certification.
        Requirements:
          - Performance score >= 70
          - At least 3 completed sessions
          - At least 5 letters mastered
        """
        sid = str(student_id)

        score_result = _scoring.calculate_performance_score(db, sid)
        score_data   = score_result["data"]
        final_score  = score_data["final_score"]

        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == sid,
            PracticeSession.status     == "completed"
        ).count()

        mastered = db.query(AlphabetState).filter(
            AlphabetState.student_id == sid,
            AlphabetState.state      == "mastered"
        ).count()

        requirements = {
            "performance_score": {
                "required": 70.0,
                "achieved": final_score,
                "met":      final_score >= 70.0
            },
            "sessions_completed": {
                "required": 3,
                "achieved": sessions,
                "met":      sessions >= 3
            },
            "letters_mastered": {
                "required": 5,
                "achieved": mastered,
                "met":      mastered >= 5
            }
        }

        eligible  = all(r["met"] for r in requirements.values())
        unmet     = [k for k, v in requirements.items() if not v["met"]]

        # Check if already certified
        existing = db.query(Certificate).filter(
            Certificate.student_id == sid
        ).first()

        return {
            "success":   True,
            "data": {
                "student_id":     sid,
                "eligible":       eligible,
                "already_issued": existing is not None,
                "final_score":    final_score,
                "grade":          score_data["grade"],
                "requirements":   requirements,
                "unmet":          unmet,
                "message": (
                    "You are eligible for certification!" if eligible
                    else f"Complete these requirements: {', '.join(unmet)}"
                )
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Issue certificate ─────────────────────────────────────────────────

    def issue_certificate(self, db: Session, student_id: str) -> dict:
        """
        Issue a certificate if eligible.
        Stores the record in DB and awards the 'certified' badge.
        """
        sid = str(student_id)

        eligibility = self.check_eligibility(db, sid)
        elig_data   = eligibility["data"]

        if not elig_data["eligible"]:
            return {
                "success": False,
                "message": "Not yet eligible. " + elig_data["message"],
                "data":    elig_data,
                "timestamp": datetime.utcnow().isoformat()
            }

        if elig_data["already_issued"]:
            existing = db.query(Certificate).filter(
                Certificate.student_id == sid
            ).first()
            return {
                "success": True,
                "message": "Certificate already issued.",
                "data": {
                    "certificate_id": existing.certificate_id,
                    "issued_at":      existing.issued_at.isoformat(),
                    "score":          existing.score,
                    "grade":          existing.grade
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        cert = Certificate(
            student_id = sid,
            score      = elig_data["final_score"],
            grade      = elig_data["grade"],
            issued_at  = datetime.utcnow()
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)

        # Award certified badge
        self._award_badge(db, sid, "certified")

        logger.info(f"Certificate issued | student={sid} | score={elig_data['final_score']} | grade={elig_data['grade']}")

        return {
            "success": True,
            "message": "Certificate issued successfully!",
            "data": {
                "certificate_id": cert.certificate_id,
                "student_id":     sid,
                "score":          cert.score,
                "grade":          cert.grade,
                "issued_at":      cert.issued_at.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Badges ────────────────────────────────────────────────────────────

    def evaluate_and_award_badges(self, db: Session, student_id: str) -> dict:
        """
        Check all badge conditions and award any newly earned badges.
        Called after every session ends.
        """
        sid       = str(student_id)
        awarded   = []

        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == sid,
            PracticeSession.status     == "completed"
        ).all()

        mastered = db.query(AlphabetState).filter(
            AlphabetState.student_id == sid,
            AlphabetState.state      == "mastered"
        ).count()

        metrics = db.query(ProgressMetrics).filter(
            ProgressMetrics.student_id == sid
        ).order_by(ProgressMetrics.session_number.desc()).all()

        consecutive_days = self._consecutive_days(sessions)
        best_accuracy    = max((s.session_accuracy for s in sessions), default=0)
        session_count    = len(sessions)

        checks = [
            ("first_session",  session_count >= 1),
            ("five_sessions",  session_count >= 5),
            ("ten_sessions",   session_count >= 10),
            ("first_mastery",  mastered >= 1),
            ("ten_mastery",    mastered >= 10),
            ("full_alphabet",  mastered == 26),
            ("streak_3",       consecutive_days >= 3),
            ("streak_7",       consecutive_days >= 7),
            ("high_accuracy",  best_accuracy >= 90),
        ]

        for badge_id, condition in checks:
            if condition:
                result = self._award_badge(db, sid, badge_id)
                if result["newly_awarded"]:
                    awarded.append(badge_id)

        return {
            "success": True,
            "data": {
                "newly_awarded": awarded,
                "all_badges":    self.get_badges(db, sid)["data"]["badges"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_badges(self, db: Session, student_id: str) -> dict:
        """Return all badges — earned and unearned."""
        sid    = str(student_id)
        earned = db.query(Badge).filter(Badge.student_id == sid).all()
        earned_ids = {b.badge_id for b in earned}

        badges = []
        for defn in BADGE_DEFS:
            is_earned = defn["id"] in earned_ids
            entry     = {**defn, "earned": is_earned}
            if is_earned:
                b = next(b for b in earned if b.badge_id == defn["id"])
                entry["earned_at"] = b.awarded_at.isoformat()
            badges.append(entry)

        return {
            "success": True,
            "data": {
                "student_id":   sid,
                "earned_count": len(earned_ids),
                "total_badges": len(BADGE_DEFS),
                "badges":       badges
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── PDF certificate ───────────────────────────────────────────────────

    def generate_pdf_certificate(self, db: Session, student_id: str) -> bytes:
        """Generate a PDF certificate for the student."""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except ImportError:
            raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

        sid  = str(student_id)
        cert = db.query(Certificate).filter(Certificate.student_id == sid).first()

        if not cert:
            raise ValueError("No certificate found. Check eligibility and issue first.")

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            leftMargin=3*cm, rightMargin=3*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        styles = getSampleStyleSheet()
        story  = []

        gold   = colors.HexColor("#B8860B")
        navy   = colors.HexColor("#1a237e")

        title_style = styles["Title"].clone("title")
        title_style.fontSize  = 36
        title_style.textColor = navy
        title_style.spaceAfter = 12

        sub_style = styles["Heading1"].clone("sub")
        sub_style.fontSize  = 18
        sub_style.textColor = gold
        sub_style.alignment = 1

        body_style = styles["Normal"].clone("body")
        body_style.fontSize  = 14
        body_style.alignment = 1
        body_style.spaceAfter = 8

        score_style = styles["Heading1"].clone("score")
        score_style.fontSize  = 48
        score_style.textColor = navy
        score_style.alignment = 1

        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("Certificate of Achievement", title_style))
        story.append(Paragraph("Sign Language Learning & Assessment Platform", sub_style))
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("This certifies that", body_style))
        story.append(Paragraph(f"<b>{sid}</b>", sub_style))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            "has successfully demonstrated proficiency in American Sign Language (ASL) "
            "Alphabet recognition through the AI-powered learning and assessment platform.",
            body_style
        ))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"{cert.score}%", score_style))
        story.append(Paragraph(f"Grade: {cert.grade}", sub_style))
        story.append(Spacer(1, 1*cm))

        # Issuance details table
        details = [
            ["Certificate ID", cert.certificate_id],
            ["Issued On",      cert.issued_at.strftime("%B %d, %Y")],
            ["Platform",       "Infosys Springboard — Sign Language Platform"]
        ]
        t = Table(details, colWidths=[6*cm, 14*cm])
        t.setStyle(TableStyle([
            ("FONTSIZE",    (0, 0), (-1, -1), 11),
            ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR",   (0, 0), (0, -1), navy),
            ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#f5f5f5"), colors.white]),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("PADDING",     (0, 0), (-1, -1), 8),
        ]))
        story.append(t)

        doc.build(story)
        return buffer.getvalue()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _award_badge(self, db: Session, student_id: str, badge_id: str) -> dict:
        existing = db.query(Badge).filter(
            Badge.student_id == student_id,
            Badge.badge_id   == badge_id
        ).first()

        if existing:
            return {"newly_awarded": False, "badge_id": badge_id}

        badge = Badge(
            student_id = student_id,
            badge_id   = badge_id,
            awarded_at = datetime.utcnow()
        )
        db.add(badge)
        db.commit()
        logger.info(f"Badge awarded | student={student_id} | badge={badge_id}")
        return {"newly_awarded": True, "badge_id": badge_id}

    def _consecutive_days(self, sessions) -> int:
        from datetime import timedelta
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
                count += 1; expected = dates[i]
            else:
                break
        return count