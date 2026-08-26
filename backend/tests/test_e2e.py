"""
End-to-End Integration Test — Task 8
=====================================
Runs the complete learner workflow and verifies every step
produces the expected downstream DB changes.

Run: pytest backend/tests/test_e2e.py -v -s

Server must be running on http://localhost:8000
"""

import requests
import time
import pytest

import time

BASE = "http://localhost:8000/api"
EMAIL = "e2e_integration@test.com"
PASS  = "IntegrationTest123!"
SID   = None   # session id — set during test

def wait_for_server(max_retries=10):
    """Wait up to 10s for the backend to be ready."""
    for i in range(max_retries):
        try:
            r = requests.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                print(f"  Server ready after {i+1} attempt(s)")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def step(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print('='*50)


class TestEndToEnd:
    token     = None
    student_id = None
    session_id = None

    # ── Step 1: Login ─────────────────────────────────────────────────────

    def test_01_register_and_login(self):
        step("Step 1: Login")
        assert wait_for_server(), "Backend not reachable at localhost:8000"
        # Register (ok if already exists)
        try: requests.post(f"{BASE}/auth/register", json={
            "full_name": "E2E Integration", "email": EMAIL,
            "password": PASS, "role_id": 1
        })
        except Exception: pass
        res = requests.post(f"{BASE}/auth/login",
                            json={"email": EMAIL, "password": PASS})
        assert res.status_code == 200
        TestEndToEnd.token = res.json()["access_token"]

        # Get user ID
        me = requests.get(f"{BASE}/auth/me",
                          headers={"Authorization": f"Bearer {TestEndToEnd.token}"})
        TestEndToEnd.student_id = str(me.json()["data"]["user_id"])
        print(f"  ✓ Logged in | student_id={TestEndToEnd.student_id}")

    # ── Step 2: Dashboard ─────────────────────────────────────────────────

    def test_02_dashboard_loads(self):
        step("Step 2: Dashboard")
        res = requests.get(f"{BASE}/dashboard/{TestEndToEnd.student_id}")
        assert res.status_code == 200
        d = res.json()["data"]
        assert "overall_accuracy"  in d
        assert "total_sessions"    in d
        assert "mastery_percent"   in d
        print(f"  ✓ Dashboard | sessions={d['total_sessions']} | acc={d['overall_accuracy']}%")

    # ── Step 3: Get recommendations ───────────────────────────────────────

    def test_03_recommendations(self):
        step("Step 3: AI Recommendations")
        res = requests.get(f"{BASE}/state/{TestEndToEnd.student_id}/recommendations")
        assert res.status_code == 200
        d = res.json()["data"]
        assert "next_letter" in d
        print(f"  ✓ Recommended letter: {d['next_letter']}")

    # ── Step 4: Start practice session ───────────────────────────────────

    def test_04_start_session(self):
        step("Step 4: Start Practice Session")
        res = requests.post(f"{BASE}/sessions/start",
                            json={"student_id": TestEndToEnd.student_id})
        assert res.status_code == 200
        TestEndToEnd.session_id = res.json()["data"]["session_id"]
        print(f"  ✓ Session started | id={TestEndToEnd.session_id}")

    # ── Step 5: Submit attempt (simulate webcam) ──────────────────────────

    def test_05_submit_attempt(self):
        step("Step 5: Submit Assessment Attempt")
        res = requests.post(f"{BASE}/sessions/attempt", json={
            "session_id":        TestEndToEnd.session_id,
            "student_id":        TestEndToEnd.student_id,
            "target_letter":     "A",
            "predicted_letter":  "A",
            "is_correct":        True,
            "confidence":        0.94,
            "inference_time_ms": 52.0,
            "hand_detected":     True,
            "frame_valid":       True
        })
        assert res.status_code == 200
        d = res.json()["data"]
        assert d["is_correct"]        is True
        assert d["session_accuracy"]  == 100.0
        assert "letter_state"         in d
        print(f"  ✓ Attempt recorded | acc={d['session_accuracy']}% | state={d['letter_state']['state']}")

    # ── Step 6: Verify analytics updated ─────────────────────────────────

    def test_06_analytics_updated(self):
        step("Step 6: Verify Analytics Updated")
        res = requests.get(f"{BASE}/dashboard/{TestEndToEnd.student_id}")
        d   = res.json()["data"]
        assert d["total_attempts"] >= 1
        print(f"  ✓ Analytics | attempts={d['total_attempts']} | acc={d['overall_accuracy']}%")

    # ── Step 7: Verify state machine updated ─────────────────────────────

    def test_07_state_machine_updated(self):
        step("Step 7: Verify State Machine Updated")
        res = requests.get(f"{BASE}/state/{TestEndToEnd.student_id}/A")
        d   = res.json()["data"]
        assert d["state"] != "not_attempted"
        assert d["total_attempts"] >= 1
        print(f"  ✓ Letter A state: {d['state']} | attempts={d['total_attempts']}")

    # ── Step 8: Verify recommendation changed ────────────────────────────

    def test_08_recommendation_updated(self):
        step("Step 8: Verify Recommendation Updated Mid-Session")
        res = requests.get(f"{BASE}/state/{TestEndToEnd.student_id}/recommendations")
        d   = res.json()["data"]
        assert len(d["recommended_queue"]) > 0
        print(f"  ✓ Recommendations updated | next={d['next_letter']}")

    # ── Step 9: End session ───────────────────────────────────────────────

    def test_09_end_session(self):
        step("Step 9: End Session")
        res = requests.put(f"{BASE}/sessions/end/{TestEndToEnd.session_id}")
        assert res.status_code == 200
        d   = res.json()["data"]
        assert d["status"]          == "completed"
        assert "summary"            in d
        assert d["total_attempts"]  >= 1
        print(f"  ✓ Session ended | acc={d['session_accuracy']}% | duration={d['duration_seconds']}s")

    # ── Step 10: Verify session summary generated ─────────────────────────

    def test_10_session_summary(self):
        step("Step 10: Session Summary Generated")
        res = requests.get(f"{BASE}/reports/session/{TestEndToEnd.session_id}")
        assert res.status_code == 200
        d   = res.json()["data"]
        assert d["total_attempts"] >= 1
        assert "letter_breakdown"  in d
        print(f"  ✓ Session report | attempts={d['total_attempts']}")

    # ── Step 11: Verify progress metrics ─────────────────────────────────

    def test_11_progress_updated(self):
        step("Step 11: Progress Tracking Updated")
        res = requests.get(f"{BASE}/progress/{TestEndToEnd.student_id}")
        assert res.status_code == 200
        d   = res.json()["data"]
        assert d["total_sessions"] >= 1
        print(f"  ✓ Progress | sessions={d['total_sessions']} | trend={d['overall_trend']}")

    # ── Step 12: Full performance report ─────────────────────────────────

    def test_12_performance_report(self):
        step("Step 12: Performance Report Generated")
        res = requests.get(f"{BASE}/reports/student/{TestEndToEnd.student_id}")
        assert res.status_code == 200
        d   = res.json()["data"]
        assert d["total_attempts"]  >= 1
        assert "recommendations"    in d
        print(f"  ✓ Report | overall_acc={d['overall_accuracy']}% | recommendations={len(d['recommendations'])}")

    # ── Step 13: Badges evaluated ────────────────────────────────────────

    def test_13_badges_evaluated(self):
        step("Step 13: Badges Auto-Evaluated")
        res = requests.post(
            f"{BASE}/certification/{TestEndToEnd.student_id}/badges/evaluate"
        )
        assert res.status_code == 200
        d   = res.json()["data"]
        print(f"  ✓ Badges | newly_awarded={d['newly_awarded']}")

    # ── Step 14: Notifications generated ─────────────────────────────────

    def test_14_notifications_generated(self):
        step("Step 14: Notifications Generated")
        res = requests.get(f"{BASE}/notifications/{TestEndToEnd.student_id}")
        assert res.status_code == 200
        d   = res.json()["data"]
        print(f"  ✓ Notifications | count={len(d['notifications'])} | unread={d['unread_count']}")

    # ── Step 15: Performance metrics ─────────────────────────────────────

    def test_15_performance_metrics(self):
        step("Step 15: Performance Metrics")
        res = requests.get(
            f"{BASE}/performance/{TestEndToEnd.student_id}"
        )
        assert res.status_code == 200
        d   = res.json()["data"]
        if "inference_time_ms" in d:
            print(f"  ✓ Performance | avg_inference={d['inference_time_ms']['avg']}ms | fps={d['estimated_fps']}")
            print(f"    Bottleneck: {d['bottleneck']}")
        else:
            print(f"  ✓ Performance endpoint OK | {d.get('message','ok')}")
