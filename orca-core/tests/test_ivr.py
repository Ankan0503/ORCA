"""Tests for 2G Keypad IVR voice call endpoints and emergency safety alerts."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ivr_incoming_call():
    response = client.post(
        "/api/ivr/incoming-call",
        data={"caller_number": "+919876543210", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert "ORCA" in data["greeting_text"]


def test_ivr_trigger_alert():
    response = client.post(
        "/api/ivr/trigger-alert",
        json={
            "alert_type": "cyclone",
            "location_name": "Chennai Coast",
            "language": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dispatched"
    assert data["severity"] == "CRITICAL"
    assert "Chennai Coast" in data["sms_text"]
