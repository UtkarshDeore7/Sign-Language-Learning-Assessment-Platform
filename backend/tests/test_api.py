"""
End-to-End API Test Suite
=========================
Tests every major endpoint and workflow.

Run from the project root:
    pip install pytest requests
    pytest backend/tests/test_api.py -v

Requires the server to be running on http://localhost:8000
"""

import pytest
import requests
import time
import base64

BASE_URL   = "http://localhost:8000/api"
STUDENT_ID = "test_student_e2e"

# ── Minimal 1x1 white JPEG for frame tests ────────────────────────────────
DUMMY_FRAME = (
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
    "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN"
    "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
    "MjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFgABAQEAAAAAAAAAAAAAAAAABgUEB"
    "/8QAIRAAAQQCAgMAAAAAAAAAAAAAAQACAxEEEiExUWH/xAAUAQEAAAAAAAAAAAAAAAAAAAAA"
    "/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8Aqa8hkiYZGxh2jqCiIgD/2Q=="
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def session_id():
    """Create a practice session and return its ID."""
    res = requests.post(f"{BASE_URL}/sessions/start",
                        json={"student_id": STUDENT_ID})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    return data["data"]["session_id"]


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_check(self):
        res = requests.get(f"{BASE_URL}/health")
        assert res.status_code == 200

    def test_root(self):
        res = requests.get("http://localhost:8000/")
        assert res.status_code == 200
        assert "Sign Language" in res.json()["message"]


# ── Authentication ────────────────────────────────────────────────────────────

class TestAuth:
    EMAIL    = "testuser_e2e@example.com"
    PASSWORD = "TestPass123!"

    def test_register(self):
        res = requests.post(f"{BASE_URL}/auth/register", json={
            "full_name": "E2E Test User",
            "email":     self.EMAIL,
            "password":  self.PASSWORD,
            "role_id":   1
        })
        # 200 = registered, 400 = already exists (both acceptable)
        assert res.status_code in (200, 400)

    def test_login(self):
        res = requests.post(f"{BASE_URL}/auth/login", json={
            "email":    self.EMAIL,
            "password": self.PASSWORD
        })
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_login_wrong_password(self):
        res = requests.post(f"{BASE_URL}/auth/login", json={
            "email":    self.EMAIL,
            "password": "wrongpassword"
        })
        assert res.status_code == 401


# ── Sessions ──────────────────────────────────────────────────────────────────

class TestSessions:
    def test_start_session(self):
        res = requests.post(f"{BASE_URL}/sessions/start",
                            json={"student_id": STUDENT_ID})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "session_id" in data["data"]
        assert data["data"]["status"] == "active"

    def test_record_attempt(self, session_id):
        res = requests.post(f"{BASE_URL}/sessions/attempt", json={
            "session_id":        session_id,
            "student_id":        STUDENT_ID,
            "target_letter":     "A",
            "predicted_letter":  "A",
            "is_correct":        True,
            "confidence":        0.92,
            "inference_time_ms": 45.0,
            "hand_detected":     True,
            "frame_valid":       True
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["is_correct"] is True
        assert data["data"]["session_accuracy"] == 100.0

    def test_record_incorrect_attempt(self, session_id):
        res = requests.post(f"{BASE_URL}/sessions/attempt", json={
            "session_id":        session_id,
            "student_id":        STUDENT_ID,
            "target_letter":     "B",
            "predicted_letter":  "D",
            "is_correct":        False,
            "confidence":        0.45,
            "inference_time_ms": 52.0,
            "hand_detected":     True,
            "frame_valid":       True
        })
        assert res.status_code == 200
        data = res.json()
        assert data["data"]["is_correct"] is False
        assert data["data"]["incorrect_total"] == 1

    def test_reject_invalid_frame(self, session_id):
        """Frame with hand_detected=False should be rejected."""
        res = requests.post(f"{BASE_URL}/sessions/attempt", json={
            "session_id":        session_id,
            "student_id":        STUDENT_ID,
            "target_letter":     "C",
            "predicted_letter":  "C",
            "is_correct":        True,
            "confidence":        0.80,
            "inference_time_ms": 40.0,
            "hand_detected":     False,
            "frame_valid":       True
        })
        assert res.status_code == 200
        assert res.json()["success"] is False

    def test_get_session(self, session_id):
        res = requests.get(f"{BASE_URL}/sessions/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["data"]["session_id"] == session_id
        assert data["data"]["status"] == "active"

    def test_get_student_sessions(self):
        res = requests.get(f"{BASE_URL}/sessions/student/{STUDENT_ID}")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_end_session(self, session_id):
        res = requests.put(f"{BASE_URL}/sessions/end/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["status"] == "completed"
        assert "summary" in data["data"]

    def test_cannot_attempt_ended_session(self, session_id):
        res = requests.post(f"{BASE_URL}/sessions/attempt", json={
            "session_id":        session_id,
            "student_id":        STUDENT_ID,
            "target_letter":     "A",
            "predicted_letter":  "A",
            "is_correct":        True,
            "confidence":        0.9,
            "inference_time_ms": 40.0
        })
        assert res.json()["success"] is False


# ── Learner State Machine ─────────────────────────────────────────────────────

class TestLearnerState:
    def test_get_all_states(self):
        res = requests.get(f"{BASE_URL}/state/{STUDENT_ID}")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "alphabet_states" in data["data"]
        assert len(data["data"]["alphabet_states"]) == 26

    def test_get_single_state(self):
        res = requests.get(f"{BASE_URL}/state/{STUDENT_ID}/A")
        assert res.status_code == 200
        data = res.json()
        assert data["data"]["letter"] == "A"
        assert data["data"]["state"] in [
            "not_attempted", "learning", "improving",
            "mastered", "needs_revision"
        ]

    def test_state_transitioned_after_attempt(self):
        """Letter A should be in 'learning' state after our attempts."""
        res = requests.get(f"{BASE_URL}/state/{STUDENT_ID}/A")
        assert res.json()["data"]["state"] != "not_attempted"

    def test_get_recommendations(self):
        res = requests.get(f"{BASE_URL}/state/{STUDENT_ID}/recommendations")
        assert res.status_code == 200
        data = res.json()
        assert "next_letter" in data["data"]
        assert "recommended_queue" in data["data"]

    def test_state_history(self):
        res = requests.get(f"{BASE_URL}/state/{STUDENT_ID}/A/history")
        assert res.status_code == 200
        assert "transitions" in res.json()["data"]


# ── Progress & Analytics ──────────────────────────────────────────────────────

class TestProgress:
    def test_progress_overview(self):
        res = requests.get(f"{BASE_URL}/progress/{STUDENT_ID}")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_alphabet_trends(self):
        res = requests.get(f"{BASE_URL}/progress/{STUDENT_ID}/alphabet-trends")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_dashboard(self):
        res = requests.get(f"{BASE_URL}/dashboard/{STUDENT_ID}")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        d = data["data"]
        assert "total_sessions"    in d
        assert "overall_accuracy"  in d
        assert "mastery_percent"   in d
        assert "consecutive_days"  in d


# ── Reports ───────────────────────────────────────────────────────────────────

class TestReports:
    def test_student_performance_report(self):
        res = requests.get(f"{BASE_URL}/reports/student/{STUDENT_ID}")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        d = data["data"]
        assert "overall_accuracy"   in d
        assert "strongest_alphabets" in d
        assert "weakest_alphabets"   in d
        assert "recommendations"     in d

    def test_csv_export(self):
        res = requests.get(
            f"{BASE_URL}/reports/student/{STUDENT_ID}/export/csv"
        )
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert len(res.content) > 0

    def test_pdf_export(self):
        res = requests.get(
            f"{BASE_URL}/reports/student/{STUDENT_ID}/export/pdf"
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"


# ── Scoring & Certification ───────────────────────────────────────────────────

class TestCertification:
    def test_performance_score(self):
        res = requests.get(f"{BASE_URL}/score/{STUDENT_ID}")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        d = data["data"]
        assert "final_score" in d
        assert "breakdown"   in d
        assert len(d["breakdown"]) == 5   # 5 components

    def test_score_components_sum(self):
        res  = requests.get(f"{BASE_URL}/score/{STUDENT_ID}")
        bd   = res.json()["data"]["breakdown"]
        total = sum(v["contribution"] for v in bd.values())
        assert abs(total - res.json()["data"]["final_score"]) < 0.1

    def test_eligibility_check(self):
        res = requests.get(
            f"{BASE_URL}/certification/{STUDENT_ID}/eligibility"
        )
        assert res.status_code == 200
        data = res.json()
        assert "eligible"      in data["data"]
        assert "requirements"  in data["data"]
        assert "final_score"   in data["data"]

    def test_badges(self):
        res = requests.get(
            f"{BASE_URL}/certification/{STUDENT_ID}/badges"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["data"]["total_badges"] == 10

    def test_evaluate_badges(self):
        res = requests.post(
            f"{BASE_URL}/certification/{STUDENT_ID}/badges/evaluate"
        )
        assert res.status_code == 200
        assert res.json()["success"] is True


# ── Assess Frame ──────────────────────────────────────────────────────────────

class TestAssessFrame:
    def test_invalid_frame_rejected(self):
        """Non-base64 string should be rejected cleanly."""
        s_res = requests.post(f"{BASE_URL}/sessions/start",
                              json={"student_id": STUDENT_ID})
        sid   = s_res.json()["data"]["session_id"]

        res = requests.post(f"{BASE_URL}/assess/frame", json={
            "session_id":    sid,
            "student_id":    STUDENT_ID,
            "target_letter": "A",
            "frame_base64":  "not-a-real-image"
        })
        assert res.status_code == 200
        assert res.json()["success"] is False
        assert res.json()["error_code"] in (
            "INVALID_FRAME", "LOW_QUALITY", "NO_HAND"
        )
        requests.put(f"{BASE_URL}/sessions/end/{sid}")


# ── Admin & Instructor ────────────────────────────────────────────────────────

class TestAdminInstructor:
    def test_seed_roles(self):
        res = requests.post(f"{BASE_URL}/admin/seed-roles")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_admin_dashboard(self):
        res = requests.get(f"{BASE_URL}/admin/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        d = data["data"]
        assert "total_users"         in d
        assert "total_sessions"      in d
        assert "platform_accuracy"   in d
        assert "total_certificates"  in d

    def test_admin_users(self):
        res = requests.get(f"{BASE_URL}/admin/users")
        assert res.status_code == 200
        assert "users" in res.json()["data"]

    def test_admin_health(self):
        res = requests.get(f"{BASE_URL}/admin/health")
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "operational"

    def test_instructor_dashboard(self):
        res = requests.get(f"{BASE_URL}/instructor/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        d = data["data"]
        assert "total_students"     in d
        assert "class_avg_accuracy" in d
        assert "students"           in d

    def test_instructor_class_progress(self):
        res = requests.get(f"{BASE_URL}/instructor/class-progress")
        assert res.status_code == 200
        assert res.json()["success"] is True