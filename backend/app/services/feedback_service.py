class FeedbackEngine:

    FINGER_RULES = {
        "A": "Make a fist with thumb resting on the side. Keep all fingers curled tightly.",
        "B": "Hold four fingers straight up together. Tuck thumb across palm.",
        "C": "Curve all fingers and thumb to form a C shape. Keep hand relaxed.",
        "D": "Point index finger up. Curve other fingers to touch thumb forming a circle.",
        "E": "Bend all fingers down. Tuck thumb under fingers.",
        "F": "Connect index finger and thumb. Hold other three fingers up.",
        "G": "Point index finger sideways. Thumb points same direction.",
        "H": "Point index and middle finger sideways together.",
        "I": "Raise pinky finger only. Keep other fingers in fist.",
        "J": "Make I shape then draw a J in the air.",
        "K": "Index and middle finger up in V shape. Thumb between them.",
        "L": "Make L shape with index finger up and thumb out.",
        "M": "Fold three fingers over tucked thumb.",
        "N": "Fold two fingers over tucked thumb.",
        "O": "Form O shape with all fingers meeting thumb at tips.",
        "P": "K shape pointing downward.",
        "Q": "G shape pointing downward.",
        "R": "Cross index and middle fingers.",
        "S": "Make fist with thumb over fingers.",
        "T": "Make fist with thumb between index and middle fingers.",
        "U": "Hold index and middle fingers up together.",
        "V": "Hold index and middle fingers up in V shape spread apart.",
        "W": "Hold index middle and ring fingers up spread apart.",
        "X": "Hook index finger like a claw.",
        "Y": "Extend thumb and pinky. Keep other fingers curled.",
        "Z": "Draw Z in the air with index finger."
    }

    def generate_feedback(self, expected: str, predicted: str, confidence: float):
        expected = expected.upper()
        predicted = predicted.upper()
        is_correct = expected == predicted

        if is_correct and confidence >= 0.8:
            feedback_type = "excellent"
            message = f"Excellent! '{expected}' recognized correctly with high confidence."
            correction = None
        elif is_correct and confidence < 0.8:
            feedback_type = "correct_low_confidence"
            message = f"Correct! But try to make the sign clearer."
            correction = self.FINGER_RULES.get(expected, "Practice this sign more.")
        else:
            feedback_type = "incorrect"
            message = f"Incorrect. You signed '{predicted}' but expected '{expected}'."
            correction = self.FINGER_RULES.get(expected, "Practice this sign more.")

        return {
            "success": True,
            "message": "Feedback generated",
            "data": {
                "expected": expected,
                "predicted": predicted,
                "is_correct": is_correct,
                "feedback_type": feedback_type,
                "feedback_message": message,
                "correction_tip": correction,
                "confidence": confidence,
                "sign_instructions": self.FINGER_RULES.get(expected)
            },
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

    def get_practice_recommendations(self, weak_letters: list):
        recommendations = []
        for letter in weak_letters:
            recommendations.append({
                "letter": letter,
                "instruction": self.FINGER_RULES.get(letter.upper(), "Practice this sign."),
                "priority": "high"
            })
        return {
            "success": True,
            "message": "Recommendations generated",
            "data": {
                "recommendations": recommendations,
                "tip": "Focus on these letters in your next practice session."
            },
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }