from datetime import datetime
from collections import defaultdict

# In-memory store — moves to DB later
all_attempts = []

class ProgressService:

    def store_attempt(self, student_id: str, target: str, predicted: str,
                      is_correct: bool, confidence: float, inference_time: float):
        attempt = {
            "student_id": student_id,
            "target_letter": target,
            "predicted_letter": predicted,
            "is_correct": is_correct,
            "confidence": confidence,
            "inference_time_ms": inference_time,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        all_attempts.append(attempt)
        return attempt

    def get_dashboard(self, student_id: str):
        student_attempts = [a for a in all_attempts if a["student_id"] == student_id]

        if not student_attempts:
            return {
                "success": False,
                "message": "No attempts found for this student",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        total = len(student_attempts)
        correct = sum(1 for a in student_attempts if a["is_correct"])
        accuracy = round((correct / total) * 100, 2)
        avg_confidence = round(
            sum(a["confidence"] for a in student_attempts) / total, 4
        )

        # Per letter analysis
        letter_stats = defaultdict(lambda: {"correct": 0, "total": 0})
        for a in student_attempts:
            letter = a["target_letter"]
            letter_stats[letter]["total"] += 1
            if a["is_correct"]:
                letter_stats[letter]["correct"] += 1

        letter_accuracy = {
            letter: round((stats["correct"] / stats["total"]) * 100, 2)
            for letter, stats in letter_stats.items()
        }

        sorted_letters = sorted(letter_accuracy.items(), key=lambda x: x[1])
        weakest = sorted_letters[:3]
        strongest = sorted_letters[-3:][::-1]

        # Most mistaken
        wrong_attempts = [a for a in student_attempts if not a["is_correct"]]
        mistake_counts = defaultdict(int)
        for a in wrong_attempts:
            mistake_counts[a["target_letter"]] += 1
        most_mistaken = sorted(mistake_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Daily streak
        dates = sorted(set(a["date"] for a in student_attempts), reverse=True)
        streak = 0
        today = datetime.now().strftime("%Y-%m-%d")
        for date in dates:
            if date == today or streak > 0:
                streak += 1
            else:
                break

        # Recent history
        recent = sorted(student_attempts, key=lambda x: x["timestamp"], reverse=True)[:10]

        return {
            "success": True,
            "message": "Dashboard fetched successfully",
            "data": {
                "total_attempts": total,
                "correct": correct,
                "accuracy_percent": accuracy,
                "average_confidence": avg_confidence,
                "daily_streak": streak,
                "strongest_alphabets": [l for l, _ in strongest],
                "weakest_alphabets": [l for l, _ in weakest],
                "most_mistaken": [{"letter": l, "count": c} for l, c in most_mistaken],
                "letter_accuracy": letter_accuracy,
                "recent_history": recent
            },
            "timestamp": datetime.now().isoformat()
        }