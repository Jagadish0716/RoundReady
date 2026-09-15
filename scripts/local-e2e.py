"""Disposable local API smoke. Run with .venv/bin/python scripts/local-e2e.py.

Uses public gateway APIs and the trusted Compose Admin bootstrap only.
Leaves smoke accounts/history intact; never changes existing users or deletes volumes.
"""

from __future__ import annotations

import json
import secrets
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
COMPOSE = ["docker-compose", "--env-file", ".env", "-f", "infrastructure/docker-compose.yml"]
client = httpx.Client(base_url=BASE, timeout=20)
suffix = uuid4().hex[:12]
password = secrets.token_urlsafe(24)
results: dict[str, str] = {}


def call(
    method: str,
    path: str,
    token: str | None = None,
    data: object = None,
    expected: int = 200,
    key: str | None = None,
) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if key:
        headers["Idempotency-Key"] = key
    response = client.request(method, path, headers=headers, json=data)
    if response.status_code != expected:
        # Responses never include passwords; omit full success bodies/verification tokens.
        raise AssertionError(
            f"{method} {path}: expected {expected}, got {response.status_code}: "
            f"{response.text[:600]}"
        )
    return response.json() if response.content else None


def passed(name: str) -> None:
    results[name] = "PASS"
    print(f"PASS {name}", flush=True)


def login_request(email: str, expected: int = 200) -> Any:
    deadline = time.monotonic() + 70
    while time.monotonic() < deadline:
        response = client.post("/v1/auth/login", json={"email": email, "password": password})
        if response.status_code == 429:
            time.sleep(2)
            continue
        if response.status_code != expected:
            raise AssertionError(
                f"POST /v1/auth/login: expected {expected}, got {response.status_code}: "
                f"{response.text[:600]}"
            )
        return response.json()
    raise AssertionError("Timed out waiting for the local login rate-limit window")


def poll(path: str, token: str | None, predicate: Callable[[Any], bool], seconds: int = 65) -> Any:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = call("GET", path, token)
        if predicate(value):
            return value
        time.sleep(2)
    raise AssertionError(f"Timed out waiting for {path}")


def register_session(role: str) -> tuple[str, str, dict[str, Any]]:
    email = f"smoke-{role}-{suffix}-{uuid4().hex[:4]}@example.com"
    account = call(
        "POST",
        "/v1/auth/register",
        data={"email": email, "password": password, "role": role},
        expected=201,
    )
    login_request(email, expected=403)
    url = account["development_verification_url"]
    assert url, "Development email provider must be enabled"
    verification_token = parse_qs(urlparse(url).query)["token"][0]
    call("POST", "/v1/auth/verify-email", data={"token": verification_token})
    login = login_request(email)
    return account["id"], email, login


def register(role: str) -> tuple[str, str]:
    account_id, _email, login = register_session(role)
    return account_id, login["access_token"]


def wait_for_auth_rejection(path: str, token: str) -> None:
    deadline = time.monotonic() + 65
    while time.monotonic() < deadline:
        response = client.get(path, headers={"Authorization": f"Bearer {token}"})
        if response.status_code in {401, 403}:
            return
        time.sleep(1)
    raise AssertionError(f"Timed out waiting for {path} to reject the old session")


def main() -> None:
    admin_email = f"smoke-admin-{suffix}@example.com"
    # Password travels on stdin, never command arguments or logs.
    bootstrap = (
        "import asyncio,json,sys; from app.scripts.create_admin import run; "
        "d=json.load(sys.stdin); asyncio.run(run(d['email'],d['password']))"
    )
    subprocess.run(
        COMPOSE + ["exec", "-T", "auth-service", "python", "-c", bootstrap],
        input=json.dumps({"email": admin_email, "password": password}),
        text=True,
        check=True,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
    )
    admin = login_request(admin_email)["access_token"]
    interviewer_id, interviewer_email, interviewer_session = register_session("interviewer")
    interviewer = interviewer_session["access_token"]
    profile = {
        "full_name": "Local Smoke Interviewer",
        "headline": "DevOps engineer",
        "company": "Smoke Labs",
        "job_title": "Senior engineer",
        "experience_years": 8,
        "linkedin_url": "https://www.linkedin.com/in/roundready-smoke",
        "github_url": "https://github.com/roundready-smoke",
        "bio": (
            "Experienced engineer practicing infrastructure, automation "
            "and clear technical communication."
        ),
    }
    call("PUT", "/v1/interviewers/me/profile", interviewer, profile)
    call(
        "PUT",
        "/v1/interviewers/me/skills",
        interviewer,
        {
            "skills": [
                {
                    "domain": "DevOps",
                    "topic": skill.lower(),
                    "skill_name": skill,
                    "experience_years": 5,
                }
                for skill in ["Docker", "Kubernetes", "Jenkins", "Terraform"]
            ]
        },
    )
    call("PUT", "/v1/interviewers/me/availability/weekly", interviewer, {"rules": []}, expected=403)
    passed("Interviewer onboarding")
    for kind, data in [
        ("mobile", {"mobile": "+919876543210"}),
        ("company-email", {"company_email": f"engineer-{suffix}@smokelabs.example.com"}),
    ]:
        challenge = call(
            "POST", f"/v1/interviewers/me/verification/{kind}/request", interviewer, data
        )
        call(
            "POST",
            f"/v1/interviewers/me/verification/{kind}/verify",
            interviewer,
            {"challenge_id": challenge["challenge_id"], "secret": challenge["development_secret"]},
        )
    evidence = call(
        "PUT",
        "/v1/interviewers/me/verification/evidence",
        interviewer,
        {"evidence_type": "github_or_portfolio", "value_reference": profile["github_url"]},
    )
    call("POST", "/v1/interviewers/me/verification/submit", interviewer)
    review = f"/v1/interviewers/admin/interviewers/{interviewer_id}"
    assert call("GET", f"{review}/verification", admin)["status"] == "under_review"
    call("POST", f"{review}/approve", admin, expected=409)
    call("POST", f"{review}/verification/linkedin-review", admin)
    for item in evidence["evidence"]:
        if item["evidence_type"] == "github_or_portfolio":
            call(
                "POST",
                f"{review}/verification/evidence/{item['id']}/review",
                admin,
                {"status": "verified"},
            )
    for status in ["pending", "passed"]:
        call(
            "POST",
            f"{review}/verification/screening",
            admin,
            {
                "screening_status": status,
                "reviewer_notes": "Local screening completed",
                "communication_assessment": "Clear",
                "technical_assessment": "Strong",
                "overall_result": status,
            },
        )
    passed("Verification")
    approved = call("POST", f"{review}/approve", admin)
    assert approved["verification_status"] == "verified"
    passed("Admin approval")
    # A real future slot inside the normal join window permits immediate local attendance.
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    start = (now + timedelta(minutes=3)).replace(second=0, microsecond=0)
    end = start + timedelta(minutes=40)
    if end.date() != start.date():
        raise AssertionError("Run smoke before 23:15 Asia/Kolkata to keep the window on one day")
    rules = {
        "rules": [
            {
                "weekday": start.weekday(),
                "start_time": start.strftime("%H:%M:%S"),
                "end_time": end.strftime("%H:%M:%S"),
                "timezone": "Asia/Kolkata",
            }
        ]
    }
    saved = call("PUT", "/v1/interviewers/me/availability/weekly", interviewer, rules)
    assert saved == call("GET", "/v1/interviewers/me/availability/weekly", interviewer)
    passed("Availability")
    slots_path = f"/v1/public/slots?interviewer_id={interviewer_id}"
    slots = poll(slots_path, None, lambda value: len(value) >= 2)
    assert (
        datetime.fromisoformat(slots[0]["starts_at"]).astimezone(ZoneInfo("Asia/Kolkata")) == start
    )
    public = call("GET", f"/v1/public/interviewers/{interviewer_id}")
    for secret in ["account_email", "company_email", "mobile", "evidence", "development_secret"]:
        assert secret not in json.dumps(public)
    passed("Public slots")
    candidate_id, candidate = register("candidate")
    call(
        "PUT",
        "/v1/users/me/profile",
        candidate,
        {
            "full_name": "Local Smoke Candidate",
            "city": "Bengaluru",
            "experience_years": 3,
            "current_role": "Engineer",
            "target_role": "DevOps Engineer",
            "preferred_language": "English",
        },
    )
    passed("Candidate onboarding")
    slot = slots[0]
    hold = call("POST", f"/v1/booking/slots/{slot['id']}/hold", candidate)
    booking_key = str(uuid4())
    booking_data = {"slot_id": slot["id"], "hold_token": hold["hold_token"]}
    booking = call(
        "POST", "/v1/booking/bookings", candidate, booking_data, expected=201, key=booking_key
    )
    assert booking["amount_paise"] == 20000 and booking["currency"] == "INR"
    assert booking == call(
        "POST", "/v1/booking/bookings", candidate, booking_data, expected=201, key=booking_key
    )
    passed("Booking")
    payment_data = {"booking_id": booking["id"]}
    _, stranger = register("candidate")
    call("POST", "/v1/payments/orders", stranger, payment_data, expected=409, key=str(uuid4()))
    call(
        "POST",
        "/v1/payments/orders",
        candidate,
        {**payment_data, "amount_paise": 1},
        expected=422,
        key=str(uuid4()),
    )
    payment_key = str(uuid4())
    payment = call(
        "POST", "/v1/payments/orders", candidate, payment_data, expected=201, key=payment_key
    )
    assert payment["amount_paise"] == 20000 and payment["currency"] == "INR"
    complete_path = f"/v1/payments/{payment['id']}/development/complete"
    call("POST", complete_path, candidate)
    call("POST", complete_path, candidate)
    passed("₹200 local payment")
    poll(
        f"/v1/booking/bookings/{booking['id']}",
        candidate,
        lambda value: value["status"] == "confirmed",
    )
    passed("Booking confirmation")
    sessions_path = "/v1/interviews/sessions"
    sessions = poll(sessions_path, candidate, lambda value: len(value) == 1)
    session = sessions[0]
    assert session["booking_id"] == booking["id"]
    assert len(call("GET", sessions_path, interviewer)) == 1
    session_path = f"{sessions_path}/{session['id']}"
    call("GET", session_path, stranger, expected=404)
    for participant in [candidate, interviewer]:
        access = call("POST", f"{session_path}/join", participant)
        assert access["provider"] == "development"
        call(
            "POST", f"{session_path}/development/attendance", participant, {"event_type": "joined"}
        )
    assert all(x["connected"] for x in call("GET", f"{session_path}/attendance", candidate))
    for participant in [candidate, interviewer]:
        call("POST", f"{session_path}/development/attendance", participant, {"event_type": "left"})
    call("POST", f"{session_path}/complete", interviewer)
    passed("Interview session")
    rubric = call("GET", f"{session_path}/rubric", interviewer)
    feedback = {
        "criterion_scores": [
            {"key": x["key"], "score": x["maximum_score"] - 1} for x in rubric["criteria"]
        ],
        "strengths": ["Clear reasoning"],
        "improvement_areas": ["More operational examples"],
        "summary": "Good technical understanding demonstrated in the local practice session.",
        "readiness_level": "interview_ready",
    }
    call("POST", f"{session_path}/feedback", interviewer, feedback, expected=201)
    call("POST", f"{session_path}/feedback", interviewer, feedback, expected=409)
    call("GET", f"{session_path}/feedback", candidate)
    passed("Feedback")
    notifications = poll(
        "/v1/notifications/me",
        candidate,
        lambda value: any(
            x["event_type"] == "feedback.submitted.v1" and x["status"] == "sent" for x in value
        ),
    )
    call("PATCH", f"/v1/notifications/{notifications[0]['id']}/read", stranger, expected=404)
    passed("Notifications")
    call("POST", f"{review}/delete", admin, {"reason": "Smoke active booking safety"}, expected=409)
    call(
        "POST",
        f"{review}/suspend",
        admin,
        {
            "reason": "Misleading information",
            "reason_category": "Misleading information",
            "admin_note": "Local lifecycle check",
        },
    )
    wait_for_auth_rejection("/v1/auth/me", interviewer)
    call(
        "POST",
        "/v1/auth/refresh",
        data={"refresh_token": interviewer_session["refresh_token"]},
        expected=401,
    )
    blocked_login = login_request(interviewer_email, expected=403)
    assert blocked_login["error"]["code"] == "account_blocked"
    assert blocked_login["error"]["details"]["reason_category"] == "Misleading information"
    call("GET", f"/v1/public/interviewers/{interviewer_id}", expected=404)
    poll(slots_path, None, lambda value: not value)
    call("POST", f"{review}/reactivate", admin)
    deadline = time.monotonic() + 65
    while time.monotonic() < deadline:
        reactivated_login = client.post(
            "/v1/auth/login", json={"email": interviewer_email, "password": password}
        )
        if reactivated_login.status_code == 200:
            break
        time.sleep(1)
    else:
        raise AssertionError("Timed out waiting for reactivated interviewer login")
    poll(slots_path, None, lambda value: bool(value))
    disposable_id, disposable_email, disposable_session = register_session("interviewer")
    disposable = disposable_session["access_token"]
    call("PUT", "/v1/interviewers/me/profile", disposable, profile)
    delete_path = f"/v1/interviewers/admin/interviewers/{disposable_id}/delete"
    deleted = call("POST", delete_path, admin, {"reason": "Disposable smoke account cleanup"})
    assert deleted["deleted_at"] is not None
    wait_for_auth_rejection("/v1/auth/me", disposable)
    call(
        "POST",
        "/v1/auth/refresh",
        data={"refresh_token": disposable_session["refresh_token"]},
        expected=401,
    )
    disabled_login = login_request(disposable_email, expected=403)
    assert disabled_login["error"]["code"] == "account_disabled"
    call("GET", f"/v1/public/interviewers/{disposable_id}", expected=404)
    call("PUT", "/v1/interviewers/me/availability/weekly", disposable, rules, expected=401)
    call(
        "POST",
        f"/v1/interviewers/admin/interviewers/{disposable_id}/reactivate",
        admin,
        expected=409,
    )
    call(
        "POST",
        "/v1/payments/orders",
        candidate,
        {"booking_id": str(uuid4())},
        expected=409,
        key=str(uuid4()),
    )
    passed("Negative security and Admin lifecycle checks")
    print(
        json.dumps(
            {
                "results": results,
                "interviewer_id": interviewer_id,
                "candidate_id": candidate_id,
                "booking_id": booking["id"],
                "session_id": session["id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
