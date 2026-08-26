import uuid
from datetime import datetime
from typing import List, Optional

# In-memory store for now
assessment_sessions = {}

ALPHABETS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

class AssessmentService:

    def start_assessment(self, student_id: str, letter: str = None):
        """Start a new assessment session for a letter"""
        session_id = str(uuid.uuid4())
        target_letter = letter.upper() if letter else ALPHABETS[0]

        assessment_sessions[session_id] = {
            "session_id": session_id,
            "student_id": student_id,
            "target_letter": target_letter,
            "attempts": [],
            "correct": 0,
            "incorrect": 0,
            "total_attempts": 0,
            "session_accuracy": 0.0,
            "start_time": datetime.now().isoformat(),
            "status": "active"
        }

        return {
            "success": True,
            "message": f"Assessment started for letter {target_letter}",
            "data": {
                "session_id": session_id,
                "target_letter": target_letter,
                "instruction": f"Please perform the sign for letter '{target_letter}'"
            },
            "timestamp": datetime.now().isoformat()
        }

    def submit_attempt(self, session_id: str, predicted: str, confidence: float, inference_time: float):
        """Submit a prediction attempt and compare with target"""
        if session_id not in assessment_sessions:
            return {
                "success": False,
                "message": "Session not found",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        session = assessment_sessions[session_id]
        target = session["target_letter"]
        is_correct = predicted.upper() == target.upper()

        attempt = {
            "attempt_number": session["total_attempts"] + 1,
            "target_letter": target,
            "predicted_letter": predicted,
            "is_correct": is_correct,
            "confidence": confidence,
            "inference_time_ms": inference_time,
            "timestamp": datetime.now().isoformat()
        }

        session["attempts"].append(attempt)
        session["total_attempts"] += 1

        if is_correct:
            session["correct"] += 1
        else:
            session["incorrect"] += 1

        session["session_accuracy"] = round(
            (session["correct"] / session["total_attempts"]) * 100, 2
        )

        return {
            "success": True,
            "message": "Attempt recorded",
            "data": {
                "result": "✓ Correct!" if is_correct else "✗ Incorrect",
                "is_correct": is_correct,
                "target_letter": target,
                "predicted_letter": predicted,
                "confidence": confidence,
                "attempt_number": session["total_attempts"],
                "session_accuracy": session["session_accuracy"],
                "correct": session["correct"],
                "incorrect": session["incorrect"]
            },
            "timestamp": datetime.now().isoformat()
        }

    def next_letter(self, session_id: str):
        """Move to next letter"""
        if session_id not in assessment_sessions:
            return {
                "success": False,
                "message": "Session not found",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        session = assessment_sessions[session_id]
        current = session["target_letter"]
        current_idx = ALPHABETS.index(current.upper())
        next_idx = (current_idx + 1) % len(ALPHABETS)
        next_letter = ALPHABETS[next_idx]
        session["target_letter"] = next_letter

        return {
            "success": True,
            "message": f"Moving to letter {next_letter}",
            "data": {
                "session_id": session_id,
                "target_letter": next_letter,
                "instruction": f"Please perform the sign for letter '{next_letter}'"
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_session_stats(self, session_id: str):
        """Get current session statistics"""
        if session_id not in assessment_sessions:
            return {
                "success": False,
                "message": "Session not found",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        session = assessment_sessions[session_id]
        return {
            "success": True,
            "message": "Session stats fetched",
            "data": {
                "session_id": session_id,
                "target_letter": session["target_letter"],
                "total_attempts": session["total_attempts"],
                "correct": session["correct"],
                "incorrect": session["incorrect"],
                "session_accuracy": session["session_accuracy"],
                "start_time": session["start_time"]
            },
            "timestamp": datetime.now().isoformat()
        }