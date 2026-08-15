"""
Report Service
==============
Generates all reports dynamically from DB — no hardcoded values.

  1. Student Performance Report  — full career summary
  2. Session Report              — auto-generated at session end
  3. PDF export                  — uses reportlab
  4. CSV export                  — built-in csv module
"""

import io
import csv
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    PracticeSession, AssessmentAttempt,
    SessionSummary, AlphabetState, ProgressMetrics
)

logger = logging.getLogger(__name__)


class ReportService:

    # ── Student Performance Report ─────────────────────────────────────────

    def get_student_performance_report(self, db: Session, student_id: str) -> dict:
        """
        Comprehensive all-time report for a student.
        Sourced entirely from DB — no hardcoded values.
        """
        all_sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == str(student_id),
            PracticeSession.status     == "completed"
        ).all()

        all_attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.student_id == str(student_id)
        ).all()

        alphabet_states = db.query(AlphabetState).filter(
            AlphabetState.student_id == str(student_id)
        ).all()

        # ── Core metrics ──────────────────────────────────────────────────
        total_sessions = len(all_sessions)
        total_attempts = len(all_attempts)
        total_correct  = sum(1 for a in all_attempts if a.is_correct)

        overall_accuracy = round(
            (total_correct / total_attempts) * 100, 2
        ) if total_attempts else 0.0

        current_session = max(all_sessions, key=lambda s: s.start_time) \
                          if all_sessions else None
        current_accuracy = current_session.session_accuracy if current_session else 0.0

        avg_confidence = round(
            sum(a.confidence for a in all_attempts) / total_attempts, 4
        ) if total_attempts else 0.0

        avg_inference_time = round(
            sum(a.inference_time_ms for a in all_attempts) / total_attempts, 2
        ) if total_attempts else 0.0

        # ── Per-letter stats ──────────────────────────────────────────────
        letter_stats   = defaultdict(lambda: {"correct": 0, "total": 0, "confidences": []})
        confusion_map  = defaultdict(lambda: defaultdict(int))  # target → {predicted: count}
        freq_map       = defaultdict(int)

        for a in all_attempts:
            letter_stats[a.target_letter]["total"] += 1
            letter_stats[a.target_letter]["confidences"].append(a.confidence)
            freq_map[a.target_letter]             += 1
            if a.is_correct:
                letter_stats[a.target_letter]["correct"] += 1
            else:
                confusion_map[a.target_letter][a.predicted_letter] += 1

        letter_accuracy = {
            l: round((s["correct"] / s["total"]) * 100, 2) if s["total"] else 0
            for l, s in letter_stats.items()
        }

        sorted_acc = sorted(letter_accuracy.items(), key=lambda x: x[1])
        strongest  = [l for l, _ in sorted_acc[-5:][::-1]]
        weakest    = [l for l, _ in sorted_acc[:5]]

        # Most frequently practiced
        most_practiced = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)[:5]

        # Most commonly misclassified (letters with most incorrect attempts)
        misclassified = {}
        for l, preds in confusion_map.items():
            top_pred = max(preds, key=preds.get)
            misclassified[l] = {
                "confused_with": top_pred,
                "count":         preds[top_pred],
                "accuracy":      letter_accuracy.get(l, 0)
            }
        most_misclassified = sorted(
            misclassified.items(), key=lambda x: x[1]["count"], reverse=True
        )[:5]

        # ── State-based recommendations ───────────────────────────────────
        state_map = {s.letter: s.state for s in alphabet_states}
        recommendations = []
        for s in alphabet_states:
            if s.state in ("learning", "needs_revision"):
                top_confusion = ""
                confused = json.loads(s.confused_with or "{}")
                if confused:
                    top = max(confused, key=confused.get)
                    top_confusion = f" (often confused with '{top}')"
                recommendations.append(
                    f"Focus on '{s.letter}' — {s.state}{top_confusion}, "
                    f"accuracy {s.accuracy}%"
                )

        # Fill not-attempted letters
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in state_map:
                recommendations.append(f"Start practicing '{letter}' — not attempted yet")

        return {
            "success": True,
            "data": {
                "student_id":           student_id,
                "generated_at":         datetime.utcnow().isoformat(),
                "report_type":          "student_performance",

                # Core metrics
                "total_sessions":       total_sessions,
                "total_attempts":       total_attempts,
                "overall_accuracy":     overall_accuracy,
                "current_session_accuracy": current_accuracy,
                "avg_confidence":       avg_confidence,
                "avg_inference_time_ms": avg_inference_time,

                # Letter performance
                "strongest_alphabets":  strongest,
                "weakest_alphabets":    weakest,
                "most_practiced":       [{"letter": l, "attempts": c}
                                         for l, c in most_practiced],
                "most_misclassified":   [{"letter": l, **v}
                                         for l, v in most_misclassified],
                "letter_accuracy":      letter_accuracy,

                # State summary
                "alphabet_states":      {s.letter: s.state for s in alphabet_states},

                # Recommendations
                "recommendations":      recommendations[:8]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── Session Report ─────────────────────────────────────────────────────

    def get_session_report(self, db: Session, session_id: str) -> dict:
        """Auto-generated at the end of every practice session."""
        session = db.query(PracticeSession).filter(
            PracticeSession.session_id == session_id
        ).first()

        if not session:
            return {"success": False, "message": "Session not found.",
                    "data": None, "timestamp": datetime.utcnow().isoformat()}

        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.session_id == session_id
        ).order_by(AssessmentAttempt.attempt_number.asc()).all()

        letter_stats = defaultdict(lambda: {"correct": 0, "total": 0, "times": []})
        for a in attempts:
            letter_stats[a.target_letter]["total"] += 1
            letter_stats[a.target_letter]["times"].append(a.inference_time_ms)
            if a.is_correct:
                letter_stats[a.target_letter]["correct"] += 1

        letter_breakdown = {
            l: {
                "attempts":         s["total"],
                "correct":          s["correct"],
                "accuracy":         round((s["correct"] / s["total"]) * 100, 2) if s["total"] else 0,
                "avg_inference_ms": round(sum(s["times"]) / len(s["times"]), 2) if s["times"] else 0
            }
            for l, s in letter_stats.items()
        }

        summary = db.query(SessionSummary).filter(
            SessionSummary.session_id == session_id
        ).first()

        return {
            "success": True,
            "data": {
                "session_id":       session_id,
                "student_id":       session.student_id,
                "report_type":      "session",
                "generated_at":     datetime.utcnow().isoformat(),

                # Session stats
                "start_time":       session.start_time.isoformat(),
                "end_time":         session.end_time.isoformat() if session.end_time else None,
                "duration_seconds": session.total_duration_secs,
                "total_attempts":   session.total_attempts,
                "correct":          session.correct_attempts,
                "incorrect":        session.incorrect_attempts,
                "session_accuracy": session.session_accuracy,
                "avg_confidence":   session.avg_confidence,
                "avg_inference_ms": session.avg_inference_time,

                # Per-letter breakdown
                "letter_breakdown": letter_breakdown,

                # From summary
                "strongest_letters": json.loads(summary.strongest_letters) if summary else [],
                "weakest_letters":   json.loads(summary.weakest_letters)   if summary else [],
                "recommendations":   json.loads(summary.recommendations)   if summary else [],

                # Attempt timeline
                "attempts": [
                    {
                        "number":          a.attempt_number,
                        "target":          a.target_letter,
                        "predicted":       a.predicted_letter,
                        "correct":         a.is_correct,
                        "confidence":      a.confidence,
                        "inference_ms":    a.inference_time_ms,
                        "timestamp":       a.timestamp.isoformat()
                    }
                    for a in attempts
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ── CSV Export ─────────────────────────────────────────────────────────

    def export_student_csv(self, db: Session, student_id: str) -> bytes:
        """
        Export all attempts for a student as CSV.
        Returns raw bytes for FastAPI's StreamingResponse.
        """
        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.student_id == str(student_id)
        ).order_by(AssessmentAttempt.timestamp.asc()).all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Attempt #", "Session ID", "Target Letter", "Predicted Letter",
            "Correct", "Confidence", "Inference Time (ms)",
            "Gesture Accuracy", "Timestamp"
        ])

        for a in attempts:
            writer.writerow([
                a.attempt_number, a.session_id, a.target_letter,
                a.predicted_letter, "Yes" if a.is_correct else "No",
                round(a.confidence, 4), round(a.inference_time_ms, 2),
                round(a.gesture_accuracy, 2), a.timestamp.isoformat()
            ])

        return output.getvalue().encode("utf-8")

    def export_session_csv(self, db: Session, session_id: str) -> bytes:
        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.session_id == session_id
        ).order_by(AssessmentAttempt.attempt_number.asc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Attempt #", "Target", "Predicted", "Correct",
            "Confidence", "Inference Time (ms)", "Timestamp"
        ])
        for a in attempts:
            writer.writerow([
                a.attempt_number, a.target_letter, a.predicted_letter,
                "Yes" if a.is_correct else "No",
                round(a.confidence, 4), round(a.inference_time_ms, 2),
                a.timestamp.isoformat()
            ])
        return output.getvalue().encode("utf-8")

    # ── PDF Export ─────────────────────────────────────────────────────────

    def export_student_pdf(self, db: Session, student_id: str) -> bytes:
        """Generate a PDF Student Performance Report using reportlab."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            )
        except ImportError:
            raise RuntimeError(
                "reportlab is not installed. Run: pip install reportlab"
            )

        report_data = self.get_student_performance_report(db, student_id)["data"]
        buffer      = io.BytesIO()
        doc         = SimpleDocTemplate(buffer, pagesize=A4,
                                         leftMargin=2*cm, rightMargin=2*cm,
                                         topMargin=2*cm, bottomMargin=2*cm)
        styles  = getSampleStyleSheet()
        story   = []

        # Title
        story.append(Paragraph(
            "Sign Language Learning Platform", styles["Title"]
        ))
        story.append(Paragraph(
            "Student Performance Report", styles["Heading1"]
        ))
        story.append(Paragraph(
            f"Student: {student_id}  |  Generated: "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"]
        ))
        story.append(Spacer(1, 0.5*cm))

        # Core metrics table
        metrics_data = [
            ["Metric", "Value"],
            ["Total Sessions",     str(report_data["total_sessions"])],
            ["Total Attempts",     str(report_data["total_attempts"])],
            ["Overall Accuracy",   f"{report_data['overall_accuracy']}%"],
            ["Current Session Accuracy", f"{report_data['current_session_accuracy']}%"],
            ["Avg Confidence",     f"{report_data['avg_confidence']:.2%}"],
            ["Avg Inference Time", f"{report_data['avg_inference_time_ms']} ms"],
        ]
        t = Table(metrics_data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#DCE6F1")]),
            ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN",        (1, 0), (1, -1), "CENTER"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Strongest / weakest
        story.append(Paragraph("Strongest Alphabets", styles["Heading2"]))
        story.append(Paragraph(
            ", ".join(report_data["strongest_alphabets"]) or "N/A", styles["Normal"]
        ))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("Weakest Alphabets", styles["Heading2"]))
        story.append(Paragraph(
            ", ".join(report_data["weakest_alphabets"]) or "N/A", styles["Normal"]
        ))
        story.append(Spacer(1, 0.3*cm))

        # Recommendations
        story.append(Paragraph("Personalised Recommendations", styles["Heading2"]))
        for rec in report_data["recommendations"]:
            story.append(Paragraph(f"• {rec}", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        # Letter accuracy table
        if report_data["letter_accuracy"]:
            story.append(Paragraph("Per-Letter Accuracy", styles["Heading2"]))
            acc_data = [["Letter", "Accuracy (%)"]]
            for letter in sorted(report_data["letter_accuracy"]):
                acc_data.append([letter, f"{report_data['letter_accuracy'][letter]}%"])
            at = Table(acc_data, colWidths=[4*cm, 4*cm])
            at.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
                ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#DCE6F1")]),
                ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ]))
            story.append(at)

        doc.build(story)
        return buffer.getvalue()

def export_student_excel(self, db: Session, student_id: str) -> bytes:
        """
        Export full student performance report as Excel workbook.
        Three sheets: Summary, All Attempts, Session History.
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise RuntimeError("openpyxl not installed. Run: pip install openpyxl")

        from models import PracticeSession, AssessmentAttempt, SessionSummary

        wb = openpyxl.Workbook()

        # ── Styles ──────────────────────────────────────────────────────────
        header_font    = Font(bold=True, color="FFFFFF")
        header_fill    = PatternFill("solid", fgColor="1a237e")
        accent_fill    = PatternFill("solid", fgColor="4ade80")
        center         = Alignment(horizontal="center")
        thin           = Side(style="thin")
        border         = Border(left=thin, right=thin, top=thin, bottom=thin)

        def style_header(ws, row, cols):
            for col in range(1, cols + 1):
                cell = ws.cell(row=row, column=col)
                cell.font      = header_font
                cell.fill      = header_fill
                cell.alignment = center
                cell.border    = border

        def style_row(ws, row, cols, alt=False):
            fill = PatternFill("solid", fgColor="DCE6F1" if alt else "FFFFFF")
            for col in range(1, cols + 1):
                cell = ws.cell(row=row, column=col)
                cell.fill   = fill
                cell.border = border

        # ── Sheet 1: Summary ────────────────────────────────────────────────
        ws1 = wb.active
        ws1.title = "Performance Summary"

        report = self.get_student_performance_report(db, student_id)["data"]

        ws1.column_dimensions["A"].width = 30
        ws1.column_dimensions["B"].width = 20

        ws1["A1"] = "Sign Language Platform — Student Report"
        ws1["A1"].font = Font(bold=True, size=14, color="1a237e")
        ws1.merge_cells("A1:B1")

        ws1["A2"] = f"Student ID: {student_id}"
        ws1["A3"] = f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

        rows = [
            ("Total Sessions",         report["total_sessions"]),
            ("Total Attempts",         report["total_attempts"]),
            ("Overall Accuracy",       f"{report['overall_accuracy']}%"),
            ("Current Session Acc.",   f"{report['current_session_accuracy']}%"),
            ("Avg Confidence",         f"{report['avg_confidence'] * 100:.1f}%"),
            ("Avg Inference Time",     f"{report['avg_inference_time_ms']} ms"),
            ("Strongest Alphabets",    ", ".join(report["strongest_alphabets"])),
            ("Weakest Alphabets",      ", ".join(report["weakest_alphabets"])),
        ]

        ws1["A5"] = "Metric"
        ws1["B5"] = "Value"
        style_header(ws1, 5, 2)

        for i, (label, value) in enumerate(rows, start=6):
            ws1[f"A{i}"] = label
            ws1[f"B{i}"] = value
            style_row(ws1, i, 2, alt=(i % 2 == 0))

        # Per-letter accuracy
        start = 6 + len(rows) + 2
        ws1[f"A{start}"] = "Letter"
        ws1[f"B{start}"] = "Accuracy (%)"
        style_header(ws1, start, 2)
        for j, (letter, acc) in enumerate(
            sorted(report["letter_accuracy"].items()), start=start + 1
        ):
            ws1[f"A{j}"] = letter
            ws1[f"B{j}"] = acc
            style_row(ws1, j, 2, alt=(j % 2 == 0))

        # ── Sheet 2: All Attempts ───────────────────────────────────────────
        ws2 = wb.create_sheet("All Attempts")
        headers = ["#", "Session ID", "Target", "Predicted",
                   "Correct", "Confidence", "Inference (ms)", "Timestamp"]
        for col, h in enumerate(headers, 1):
            ws2.cell(row=1, column=col, value=h)
            ws2.column_dimensions[get_column_letter(col)].width = 18
        style_header(ws2, 1, len(headers))

        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.student_id == str(student_id)
        ).order_by(AssessmentAttempt.timestamp.asc()).all()

        for i, a in enumerate(attempts, start=2):
            row = [
                a.attempt_number, a.session_id[:8] + "…",
                a.target_letter, a.predicted_letter,
                "Yes" if a.is_correct else "No",
                round(a.confidence, 4), round(a.inference_time_ms, 2),
                a.timestamp.strftime("%Y-%m-%d %H:%M")
            ]
            for col, val in enumerate(row, 1):
                ws2.cell(row=i, column=col, value=val)
            style_row(ws2, i, len(headers), alt=(i % 2 == 0))

        # ── Sheet 3: Session History ────────────────────────────────────────
        ws3 = wb.create_sheet("Session History")
        s_headers = ["Session #", "Date", "Duration (s)",
                     "Attempts", "Correct", "Accuracy (%)", "Avg Confidence"]
        for col, h in enumerate(s_headers, 1):
            ws3.cell(row=1, column=col, value=h)
            ws3.column_dimensions[get_column_letter(col)].width = 16
        style_header(ws3, 1, len(s_headers))

        sessions = db.query(PracticeSession).filter(
            PracticeSession.student_id == str(student_id),
            PracticeSession.status     == "completed"
        ).order_by(PracticeSession.created_at.asc()).all()

        for i, s in enumerate(sessions, start=2):
            row = [
                i - 1,
                s.start_time.strftime("%Y-%m-%d %H:%M"),
                s.total_duration_secs,
                s.total_attempts,
                s.correct_attempts,
                s.session_accuracy,
                round(s.avg_confidence * 100, 1)
            ]
            for col, val in enumerate(row, 1):
                ws3.cell(row=i, column=col, value=val)
            style_row(ws3, i, len(s_headers), alt=(i % 2 == 0))

        # ── Save ────────────────────────────────────────────────────────────
        import io
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()