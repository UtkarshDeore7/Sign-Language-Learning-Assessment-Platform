from datetime import datetime
from collections import defaultdict
from typing import List, Dict

class ErrorAnalysisService:

    def analyze(self, attempts: List[Dict]):
        if not attempts:
            return {
                "success": False,
                "message": "No attempts found",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

        confused_pairs = defaultdict(int)
        for a in attempts:
            if not a["is_correct"]:
                pair = f"{a['target_letter']} → {a['predicted_letter']}"
                confused_pairs[pair] += 1

        top_confused = sorted(
            confused_pairs.items(), key=lambda x: x[1], reverse=True
        )[:5]

        letter_confidence = defaultdict(list)
        for a in attempts:
            letter_confidence[a["target_letter"]].append(a["confidence"])

        avg_confidence_per_letter = {
            letter: round(sum(confs) / len(confs), 4)
            for letter, confs in letter_confidence.items()
        }
        low_confidence = {
            k: v for k, v in avg_confidence_per_letter.items()
            if v < 0.7
        }

        mistake_counts = defaultdict(int)
        for a in attempts:
            if not a["is_correct"]:
                mistake_counts[a["target_letter"]] += 1

        repeated_mistakes = {
            k: v for k, v in mistake_counts.items()
            if v >= 2
        }

        letter_attempts = defaultdict(list)
        for a in attempts:
            letter_attempts[a["target_letter"]].append(a["is_correct"])

        letter_accuracy = {}
        for letter, results in letter_attempts.items():
            accuracy = round(sum(results) / len(results) * 100, 2)
            letter_accuracy[letter] = accuracy

        needs_revision = {
            k: v for k, v in letter_accuracy.items()
            if v < 60
        }

        improvement_trend = {}
        for letter, results in letter_attempts.items():
            if len(results) >= 4:
                first_half = results[:len(results)//2]
                second_half = results[len(results)//2:]
                first_acc = sum(first_half) / len(first_half)
                second_acc = sum(second_half) / len(second_half)
                diff = round((second_acc - first_acc) * 100, 2)
                if diff > 5:
                    trend = "improving"
                elif diff < -5:
                    trend = "declining"
                else:
                    trend = "stable"
                improvement_trend[letter] = {
                    "trend": trend,
                    "change_percent": diff
                }

        return {
            "success": True,
            "message": "Error analysis complete",
            "data": {
                "top_confused_pairs": [
                    {"pair": p, "count": c} for p, c in top_confused
                ],
                "low_confidence_alphabets": low_confidence,
                "repeated_mistakes": repeated_mistakes,
                "needs_immediate_revision": needs_revision,
                "improvement_trends": improvement_trend,
                "letter_accuracy": letter_accuracy,
                "generated_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }