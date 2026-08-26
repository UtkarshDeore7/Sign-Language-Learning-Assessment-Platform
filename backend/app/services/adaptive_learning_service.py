"""
Adaptive Learning Service
=========================
Legacy orchestration service — kept for backward compatibility.
New code should use POST /api/assess/frame which does this automatically.
"""

from datetime import datetime
from services.learning_journey_service import LearningJourneyService
from services.feedback_service import FeedbackEngine
from services.error_analysis_service import ErrorAnalysisService

journey_service       = LearningJourneyService()
feedback_engine       = FeedbackEngine()
error_analysis_service = ErrorAnalysisService()


class AdaptiveLearningService:

    def process_attempt(
        self,
        session_id: str,
        student_id: str,
        predicted: str,
        confidence: float,
        time_taken_ms: float
    ):
        """
        Legacy endpoint — kept for compatibility.
        Requires session to already be started via POST /api/sessions/start
        and prediction to come from POST /api/predict.

        For full pipeline (frame → validate → predict → record → feedback),
        use POST /api/assess/frame instead.
        """
        # Update in-memory learner journey profile
        journey_service.update_profile(
            student_id, predicted, predicted,
            True, confidence
        )

        # Generate feedback
        feedback = feedback_engine.generate_feedback(
            predicted, predicted, confidence
        )

        # Recommendations from journey
        recommendations = journey_service.generate_recommendations(student_id)

        # Error analysis — empty list is handled gracefully
        error_analysis = error_analysis_service.analyze([])

        profile = journey_service.get_profile(student_id)

        return {
            "success": True,
            "message": (
                "Attempt processed. "
                "Note: use POST /api/assess/frame for the full assessment pipeline."
            ),
            "data": {
                "session_id":         session_id,
                "student_id":         student_id,
                "predicted":          predicted,
                "confidence":         confidence,
                "feedback":           feedback.get("data"),
                "next_recommendation": recommendations["data"].get("next_letter"),
                "recommended_queue":   recommendations["data"].get("recommended_queue", [])[:3],
                "error_insights":      error_analysis.get("data"),
                "learner_profile":     profile.get("data"),
                "workflow_completed_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }