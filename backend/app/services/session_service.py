import uuid
from datetime import datetime

# In-memory store for now — moves to DB later without changing interface
sessions = {}

class SessionService:
    def start_session(self, lesson_id: int):
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "session_id": session_id,
            "lesson_id": lesson_id,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "attempts": 0
        }
        return {
            "success": True,
            "message": "Practice session started.",
            "data": sessions[session_id],
            "timestamp": datetime.now().isoformat()
        }

    def end_session(self, session_id: str):
        if session_id not in sessions:
            return {
                "success": False,
                "message": "Session not found.",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }
        sessions[session_id]["end_time"] = datetime.now().isoformat()
        return {
            "success": True,
            "message": "Session ended.",
            "data": sessions[session_id],
            "timestamp": datetime.now().isoformat()
        }

    def increment_attempt(self, session_id: str):
        if session_id in sessions:
            sessions[session_id]["attempts"] += 1
        return sessions.get(session_id)

    def get_session(self, session_id: str):
        session = sessions.get(session_id)
        if not session:
            return {
                "success": False,
                "message": "Session not found.",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }
        return {
            "success": True,
            "message": "Session fetched.",
            "data": session,
            "timestamp": datetime.now().isoformat()
        }