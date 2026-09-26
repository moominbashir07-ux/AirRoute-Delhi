"""
Comprehensive Test Suite for EmailJS OTP Authentication.
Validates security controls, rate limiting, hashing, brute-force resistance,
and single-use invalidation.
"""

import os
import json
import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app import app
from database import (
    init_db, get_connection, save_otp, verify_otp, delete_otp,
    can_request_otp, create_user, get_user_by_email, create_or_get_user
)
from email_service import send_otp_email, is_emailjs_configured


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_test_otps():
    """Ensure clean database state for test emails before and after each test."""
    test_emails = [
        "valid_user@example.com",
        "invalid_test@example.com",
        "cooldown_test@example.com",
        "brute_force_test@example.com",
        "expiry_test@example.com",
        "reuse_test@example.com",
        "failure_test@example.com",
        "restart_test@example.com",
        "signup_flow@example.com",
        "smoke_tester@example.com"
    ]
    conn = get_connection()
    cursor = conn.cursor()
    for email in test_emails:
        cursor.execute("DELETE FROM otps WHERE email = ?", (email,))
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    yield
    conn = get_connection()
    cursor = conn.cursor()
    for email in test_emails:
        cursor.execute("DELETE FROM otps WHERE email = ?", (email,))
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()


def test_valid_email_send_otp(client):
    """Test 1: Valid email receives successful OTP dispatch response without leaking OTP."""
    response = client.post("/auth/send-otp", json={"email": "valid_user@example.com", "name": "Valid User"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "OTP sent to your email."
    assert "cooldown" in data
    # Security requirement: Plaintext OTP must NEVER be returned
    assert "otp" not in data
    assert "dev_otp" not in data


def test_invalid_email_rejected(client):
    """Test 2: Invalid emails are rejected with HTTP 400 Bad Request."""
    invalid_emails = [
        "",
        "notanemail",
        "user@",
        "@domain.com",
        "spaces in@email.com",
        "a" * 250 + "@long.com"
    ]
    for email in invalid_emails:
        response = client.post("/auth/send-otp", json={"email": email})
        assert response.status_code in (400, 422)


def test_otp_email_successfully_sent_via_emailjs():
    """Test 3: EmailJS REST API dispatch formats payload correctly."""
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = b"OK"
    mock_response.__enter__.return_value = mock_response

    with patch.dict(os.environ, {
        "EMAILJS_SERVICE_ID": "test_service",
        "EMAILJS_TEMPLATE_ID": "test_template",
        "EMAILJS_PUBLIC_KEY": "test_public_key"
    }):
        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            success, msg = send_otp_email("valid_user@example.com", "123456", "Test User")
            assert success is True
            assert "dispatched successfully" in msg
            assert mock_urlopen.called

            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            assert payload["service_id"] == "test_service"
            assert payload["template_id"] == "test_template"
            assert payload["user_id"] == "test_public_key"
            assert payload["template_params"]["to_email"] == "valid_user@example.com"
            assert payload["template_params"]["otp"] == "123456"


def test_incorrect_otp_fails(client):
    """Test 4: Submitting an incorrect OTP code fails and reports remaining attempts."""
    email = "invalid_test@example.com"
    save_otp(email, "654321", expires_in_seconds=300, max_attempts=5)

    response = client.post("/auth/verify-otp", json={"email": email, "otp": "111111"})
    assert response.status_code == 400
    data = response.json()
    assert "Invalid verification code" in data["detail"]
    assert "4 attempt(s) remaining" in data["detail"]


def test_correct_otp_authenticates(client):
    """Test 5: Submitting correct OTP authenticates user and returns user session."""
    email = "valid_user@example.com"
    save_otp(email, "554433", expires_in_seconds=300, max_attempts=5)

    response = client.post("/auth/verify-otp", json={"email": email, "otp": "554433", "name": "Verified User"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == email
    assert data["user"]["name"] == "Verified User"


def test_expired_otp_rejected(client):
    """Test 6: Expired OTP codes are rejected and purged from database."""
    email = "expiry_test@example.com"
    # Save OTP that expired 10 seconds ago
    save_otp(email, "998877", expires_in_seconds=-10, max_attempts=5)

    response = client.post("/auth/verify-otp", json={"email": email, "otp": "998877"})
    assert response.status_code == 400
    data = response.json()
    assert "expired" in data["detail"].lower()


def test_reused_otp_rejected(client):
    """Test 7: OTP cannot be reused once verified (single-use enforcement)."""
    email = "reuse_test@example.com"
    save_otp(email, "123123", expires_in_seconds=300, max_attempts=5)

    # First verification must succeed
    res1 = client.post("/auth/verify-otp", json={"email": email, "otp": "123123"})
    assert res1.status_code == 200

    # Second verification with same code must fail
    res2 = client.post("/auth/verify-otp", json={"email": email, "otp": "123123"})
    assert res2.status_code == 400
    assert "No active verification code found" in res2.json()["detail"]


def test_multiple_incorrect_otp_attempts_locks(client):
    """Test 8: Exceeding maximum failed attempts locks/deletes the OTP."""
    email = "brute_force_test@example.com"
    save_otp(email, "777888", expires_in_seconds=300, max_attempts=3)

    # Attempt 1
    res1 = client.post("/auth/verify-otp", json={"email": email, "otp": "000001"})
    assert res1.status_code == 400
    assert "2 attempt(s) remaining" in res1.json()["detail"]

    # Attempt 2
    res2 = client.post("/auth/verify-otp", json={"email": email, "otp": "000002"})
    assert res2.status_code == 400
    assert "1 attempt(s) remaining" in res2.json()["detail"]

    # Attempt 3: Exhausted
    res3 = client.post("/auth/verify-otp", json={"email": email, "otp": "000003"})
    assert res3.status_code == 400
    assert "Maximum attempts exceeded" in res3.json()["detail"]

    # Attempt 4: Should be deleted completely
    res4 = client.post("/auth/verify-otp", json={"email": email, "otp": "777888"})
    assert res4.status_code == 400
    assert "No active verification code found" in res4.json()["detail"]


def test_resend_cooldown_enforced(client):
    """Test 9 & 10: Resend cooldown prevents rapid repeated OTP requests (HTTP 429)."""
    email = "cooldown_test@example.com"

    # First send: Success
    res1 = client.post("/auth/send-otp", json={"email": email})
    assert res1.status_code == 200

    # Immediate second send: Must be rate-limited
    res2 = client.post("/auth/send-otp", json={"email": email})
    assert res2.status_code == 429
    assert "Please wait" in res2.json()["detail"]
    assert "retry_after" in res2.json()


def test_emailjs_failure_handling(client):
    """Test 11: When EmailJS delivery fails, API returns HTTP 502 and does not leave active OTP."""
    email = "failure_test@example.com"

    with patch("app.send_otp_email", return_value=(False, "Connection timed out")):
        res = client.post("/auth/send-otp", json={"email": email})
        assert res.status_code == 502
        assert "Failed to dispatch verification email" in res.json()["detail"]

    # Verify no dangling OTP was stored in database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM otps WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    assert row is None


def test_server_restart_persistence():
    """Test 12: Hashed OTP stored in SQLite persists across re-initialization (server restart)."""
    email = "restart_test@example.com"
    save_otp(email, "842615", expires_in_seconds=300, max_attempts=5)

    # Simulate server restart by calling init_db again
    init_db()

    # OTP should still verify successfully
    success, msg = verify_otp(email, "842615")
    assert success is True
    assert msg == "OTP verified successfully."


def test_unauthenticated_protected_route(client):
    """Test 13: Protected endpoints cannot be invoked unauthenticated."""
    res = client.post("/train")
    assert res.status_code in (401, 403)


def test_signup_with_otp_flow(client):
    """Test 14 & 15: Full registration flow with OTP verification."""
    email = "signup_flow@example.com"
    save_otp(email, "456789", expires_in_seconds=300, max_attempts=5)

    res = client.post("/auth/signup", json={
        "name": "Flow User",
        "email": email,
        "password": "strongPassword123",
        "otp": "456789"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == email

    # User can now login with password
    login_res = client.post("/auth/login", json={
        "email": email,
        "password": "strongPassword123"
    })
    assert login_res.status_code == 200
    assert login_res.json()["user"]["email"] == email
