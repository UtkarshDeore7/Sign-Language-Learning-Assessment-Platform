import uuid
import time
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, asdict

@dataclass
class AssessmentRecord:
    record_id: str
    session_id: str
    student_id: str
    attempt_number: int
    expected_gesture: str
    predicted_gesture: str
    is_correct: bool
    confidence: float
    overall_gesture_accuracy: float
    session_accuracy: float
    time_taken_ms: float
    timestamp: str

assessment_records = []
assessment_sessions = {}

class AssessmentEngine:

    def start_session(self, student_id: str, target_letter: str):
        session_id = str(uuid.uuid4())
        assessment_sessions[session_id] = {
            "session_id": session_id,
            "student_id": student_id,
            "target_letter": target_letter.upper(),
            "attempts": 0,
            "correct": 0,
            "start_time": datetime.now().isoformat()
        }
        return {
            "success": True,
            "message": f"Assessment session started for letter {target_letter.upper()}",
            "data": {
                "session_id": session_id,
                "expected_gesture": target_letter.upper(),
                "instruction": f"Perform the sign for letter '{target_letter.upper()}'"
            },
            "timestamp": datetime.now().isoformat()
        }

    def evaluate(self, session_id: str, predicted: str,
                 confidence: float, time_taken_ms: float):
        if session_id not in assessment_sessions:
            return {
                "success": False,
                "message": "Session not found",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        session = assessment_sessions[session_id]
        expected = session["target_letter"]
        is_correct = predicted.upper() == expected.upper()

        session["attempts"] += 1
        if is_correct:
            session["correct"] += 1

        session_accuracy = round(
            (session["correct"] / session["attempts"]) * 100, 2
        )

        # Gesture accuracy based on confidence when correct
        gesture_accuracy = round(confidence * 100, 2) if is_correct else round((1 - confidence) * 100, 2)

        record = AssessmentRecord(
            record_id=str(uuid.uuid4()),
            session_id=session_id,
            student_id=session["student_id"],
            attempt_number=session["attempts"],
            expected_gesture=expected,
            predicted_gesture=predicted.upper(),
            is_correct=is_correct,
            confidence=round(confidence, 4),
            overall_gesture_accuracy=gesture_accuracy,
            session_accuracy=session_accuracy,
            time_taken_ms=round(time_taken_ms, 2),
            timestamp=datetime.now().isoformat()
        )

        assessment_records.append(asdict(record))

        return {
            "success": True,
            "message": "Assessment evaluated",
            "data": {
                "record_id": record.record_id,
                "expected_gesture": expected,
                "predicted_gesture": predicted.upper(),
                "result": "✓ Correct!" if is_correct else "✗ Incorrect",
                "is_correct": is_correct,
                "confidence": record.confidence,
                "overall_gesture_accuracy": gesture_accuracy,
                "attempt_number": session["attempts"],
                "session_accuracy": session_accuracy,
                "time_taken_ms": record.time_taken_ms
            },
            "timestamp": record.timestamp
        }

    def generate_report(self, session_id: str):
        records = [r for r in assessment_records if r["session_id"] == session_id]

        if not records:
            return {
                "success": False,
                "message": "No records found",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        total = len(records)
        correct = sum(1 for r in records if r["is_correct"])
        incorrect = total - correct
        overall_score = round((correct / total) * 100, 2)
        avg_confidence = round(sum(r["confidence"] for r in records) / total, 4)
        avg_time = round(sum(r["time_taken_ms"] for r in records) / total, 2)

        # Gesture wise performance
        gesture_stats = {}
        for r in records:
            g = r["expected_gesture"]
            if g not in gesture_stats:
                gesture_stats[g] = {"correct": 0, "total": 0}
            gesture_stats[g]["total"] += 1
            if r["is_correct"]:
                gesture_stats[g]["correct"] += 1

        gesture_accuracy = {
            g: round((s["correct"]/s["total"])*100, 2)
            for g, s in gesture_stats.items()
        }

        difficult = sorted(gesture_accuracy.items(), key=lambda x: x[1])[:3]

        # Improvement across attempts
        improvement = [
            {"attempt": r["attempt_number"], "correct": r["is_correct"],
             "confidence": r["confidence"]}
            for r in records
        ]

        report = {
            "session_id": session_id,
            "total_attempts": total,
            "correct": correct,
            "incorrect": incorrect,
            "overall_score": overall_score,
            "average_confidence": avg_confidence,
            "average_response_time_ms": avg_time,
            "gesture_performance": gesture_accuracy,
            "most_difficult_gestures": [g for g, _ in difficult],
            "improvement_trend": improvement,
            "generated_at": datetime.now().isoformat()
        }

        return {
            "success": True,
            "message": "Assessment report generated",
            "data": report,
            "timestamp": datetime.now().isoformat()
        }