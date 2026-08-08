from datetime import datetime
from collections import defaultdict
from typing import Dict, List

learner_profiles = {}

MASTERY_LEVELS = {
    "novice": (0, 40),
    "beginner": (40, 60),
    "intermediate": (60, 80),
    "advanced": (80, 95),
    "mastered": (95, 101)
}

def get_mastery_level(accuracy: float) -> str:
    for level, (low, high) in MASTERY_LEVELS.items():
        if low <= accuracy < high:
            return level
    return "novice"

class LearningJourneyService:

    def get_or_create_profile(self, student_id: str) -> Dict:
        if student_id not in learner_profiles:
            learner_profiles[student_id] = {
                "student_id": student_id,
                "total_attempts": 0,
                "alphabet_stats": {},
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        return learner_profiles[student_id]

    def update_profile(self, student_id: str, target: str,
                      predicted: str, is_correct: bool, confidence: float):
        profile = self.get_or_create_profile(student_id)
        profile["total_attempts"] += 1
        profile["last_updated"] = datetime.now().isoformat()

        if target not in profile["alphabet_stats"]:
            profile["alphabet_stats"][target] = {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
                "mastery_level": "novice",
                "avg_confidence": 0.0,
                "confidences": [],
                "consecutive_correct": 0,
                "consecutive_incorrect": 0,
                "confused_with": defaultdict(int),
                "last_practiced": None
            }

        stats = profile["alphabet_stats"][target]
        stats["total"] += 1
        stats["last_practiced"] = datetime.now().isoformat()
        stats["confidences"].append(confidence)
        stats["avg_confidence"] = round(
            sum(stats["confidences"]) / len(stats["confidences"]), 4
        )

        if is_correct:
            stats["correct"] += 1
            stats["consecutive_correct"] += 1
            stats["consecutive_incorrect"] = 0
        else:
            stats["consecutive_incorrect"] += 1
            stats["consecutive_correct"] = 0
            stats["confused_with"][predicted] += 1

        stats["accuracy"] = round(
            (stats["correct"] / stats["total"]) * 100, 2
        )
        stats["mastery_level"] = get_mastery_level(stats["accuracy"])

        return {
            "success": True,
            "message": "Profile updated",
            "data": {
                "student_id": student_id,
                "target": target,
                "mastery_level": stats["mastery_level"],
                "accuracy": stats["accuracy"],
                "total_attempts": profile["total_attempts"]
            },
            "timestamp": datetime.now().isoformat()
        }

    def generate_recommendations(self, student_id: str) -> Dict:
        profile = self.get_or_create_profile(student_id)
        stats = profile["alphabet_stats"]

        if not stats:
            return {
                "success": True,
                "message": "Recommendations generated",
                "data": {
                    "recommended_queue": [
                        {"letter": "A", "reason": "Start with the basics",
                         "priority": "high"}
                    ],
                    "total_recommendations": 1,
                    "next_letter": "A"
                },
                "timestamp": datetime.now().isoformat()
            }

        recommendations = []
        all_letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        for letter in all_letters:
            if letter not in stats:
                recommendations.append({
                    "letter": letter,
                    "reason": "Not practiced yet",
                    "priority": "medium"
                })
                continue

            s = stats[letter]

            if s["mastery_level"] in ["novice", "beginner"]:
                confused = dict(s["confused_with"])
                top_confused = max(confused, key=confused.get) if confused else None
                reason = f"Low mastery ({s['mastery_level']})"
                if top_confused:
                    reason += f" — often confused with {top_confused}"
                recommendations.append({
                    "letter": letter,
                    "reason": reason,
                    "priority": "high"
                })
            elif s["consecutive_incorrect"] >= 3:
                recommendations.append({
                    "letter": letter,
                    "reason": f"Failed {s['consecutive_incorrect']} times in a row",
                    "priority": "high"
                })
            elif s["avg_confidence"] < 0.7 and s["accuracy"] > 70:
                recommendations.append({
                    "letter": letter,
                    "reason": "Low confidence despite correct predictions",
                    "priority": "medium"
                })
            else:
                recommendations.append({
                    "letter": letter,
                    "reason": "High improvement trend — ready to progress",
                    "priority": "low"
                })

        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order[x["priority"]])

        return {
            "success": True,
            "message": "Recommendations generated",
            "data": {
                "recommended_queue": recommendations[:10],
                "total_recommendations": len(recommendations),
                "next_letter": recommendations[0]["letter"] if recommendations else "A"
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_profile(self, student_id: str) -> Dict:
        profile = self.get_or_create_profile(student_id)
        stats = profile["alphabet_stats"]

        clean_stats = {}
        for letter, s in stats.items():
            clean_stats[letter] = {
                "total": s["total"],
                "correct": s["correct"],
                "accuracy": s["accuracy"],
                "mastery_level": s["mastery_level"],
                "avg_confidence": s["avg_confidence"],
                "consecutive_correct": s["consecutive_correct"],
                "consecutive_incorrect": s["consecutive_incorrect"],
                "confused_with": dict(s["confused_with"]),
                "last_practiced": s["last_practiced"]
            }

        return {
            "success": True,
            "message": "Learner profile fetched",
            "data": {
                "student_id": student_id,
                "total_attempts": profile["total_attempts"],
                "alphabet_stats": clean_stats,
                "last_updated": profile["last_updated"]
            },
            "timestamp": datetime.now().isoformat()
        }