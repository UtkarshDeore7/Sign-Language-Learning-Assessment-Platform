from datetime import datetime
from collections import defaultdict

class ReviewService:

    def generate_review(self, session_id: str, attempts: list):
        """
        Generate practice review after session ends.
        attempts: list of assessment records
        """
        if not attempts:
            return {
                "success": False,
                "message": "No attempts found",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        total = len(attempts)
        correct = sum(1 for a in attempts if a["is_correct"])
        incorrect = total - correct
        overall_score = round((correct / total) * 100, 2)

        # Confidence trend
        confidence_trend = [
            {"attempt": i+1, "confidence": a["confidence"]}
            for i, a in enumerate(attempts)
        ]

        # Most common mistakes
        mistakes = defaultdict(int)
        for a in attempts:
            if not a["is_correct"]:
                mistakes[a["predicted_gesture"]] += 1
        common_mistakes = sorted(mistakes.items(), key=lambda x: x[1], reverse=True)[:5]

        # Gesture specific feedback
        gesture_feedback = {}
        for a in attempts:
            g = a["expected_gesture"]
            if g not in gesture_feedback:
                gesture_feedback[g] = {"correct": 0, "total": 0, "avg_confidence": []}
            gesture_feedback[g]["total"] += 1
            if a["is_correct"]:
                gesture_feedback[g]["correct"] += 1
            gesture_feedback[g]["avg_confidence"].append(a["confidence"])

        gesture_summary = {}
        for g, stats in gesture_feedback.items():
            acc = round((stats["correct"] / stats["total"]) * 100, 2)
            avg_conf = round(sum(stats["avg_confidence"]) / len(stats["avg_confidence"]), 4)
            gesture_summary[g] = {
                "accuracy": acc,
                "average_confidence": avg_conf,
                "status": "Strong" if acc >= 80 else "Needs Practice"
            }

        # Weakest gestures for recommendations
        weakest = sorted(gesture_summary.items(), key=lambda x: x[1]["accuracy"])[:3]
        recommendations = [
            f"Practice letter '{g}' more — current accuracy {stats['accuracy']}%"
            for g, stats in weakest if stats["accuracy"] < 100
        ]

        return {
            "success": True,
            "message": "Practice review generated",
            "data": {
                "session_id": session_id,
                "overall_score": overall_score,
                "total_attempts": total,
                "correct": correct,
                "incorrect": incorrect,
                "confidence_trend": confidence_trend,
                "most_common_mistakes": [
                    {"predicted": m, "count": c} for m, c in common_mistakes
                ],
                "gesture_summary": gesture_summary,
                "recommendations": recommendations,
                "generated_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }