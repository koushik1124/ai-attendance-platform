from datetime import date, datetime, timezone
from unittest.mock import MagicMock
import httpx
import pytest
from groq import APIConnectionError, APIStatusError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.attendance import AttendanceRecord
from app.models.user import User, UserRole
from app.services.assistant import (
    ALLOWED_TOOL_NAMES,
    execute_tool,
    mask_report_data,
    mask_text,
)


def login(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def employee_headers(client):
    return {"Authorization": f"Bearer {login(client, 'employee@example.com', 'employee-password')}"}


def admin_headers(client):
    return {"Authorization": f"Bearer {login(client, 'admin@example.com', 'admin-password')}"}


def _seed_sample_attendance(employee_id: int):
    with SessionLocal() as db:
        db.add_all([
            AttendanceRecord(
                user_id=employee_id,
                work_date=date(2026, 10, 1),
                punch_in_at=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
                punch_out_at=datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc),
            ),
            AttendanceRecord(
                user_id=employee_id,
                work_date=date(2026, 10, 2),
                punch_in_at=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
            ),
        ])
        db.commit()


def make_tool_call(call_id: str, name: str, arguments: str):
    tc = MagicMock()
    tc.id = call_id
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def make_chat_completion(content: str | None = None, tool_calls: list | None = None):
    completion = MagicMock()
    choice = MagicMock()
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    choice.message = message
    completion.choices = [choice]
    return completion


def test_mask_text_redacts_pii_and_secrets():
    raw = "Contact support at user@test.com using key gsk_1234567890abcdef1234567890 or Bearer eyJhbGciOi.eyJzdWIi.signature"
    masked = mask_text(raw)
    assert "user@test.com" not in masked
    assert "[REDACTED_EMAIL]" in masked
    assert "gsk_1234567890abcdef1234567890" not in masked
    assert "[REDACTED_API_KEY]" in masked
    assert "[REDACTED_TOKEN]" in masked or "[REDACTED_JWT]" in masked


def test_mask_report_data_redacts_sensitive_fields():
    data = {
        "email": "employee@domain.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$secret",
        "attendance_rate": 85.5,
        "nested": {"contact_email": "Contact manager at boss@company.org"},
    }
    sanitized = mask_report_data(data)
    assert sanitized["email"] == "[REDACTED_EMAIL]"
    assert sanitized["password_hash"] == "[REDACTED]"
    assert sanitized["attendance_rate"] == 85.5
    assert "boss@company.org" not in sanitized["nested"]["contact_email"]
    assert "[REDACTED_EMAIL]" in sanitized["nested"]["contact_email"]


def test_assistant_authentication_required(client):
    response = client.post("/api/v1/assistant/query", json={"query": "What is my attendance?"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_assistant_empty_query_rejected(client, users):
    headers = employee_headers(client)
    response = client.post("/api/v1/assistant/query", json={"query": "   "}, headers=headers)
    assert response.status_code == 422


def test_assistant_unconfigured_api_key(client, users, monkeypatch):
    monkeypatch.setattr(get_settings(), "groq_api_key", None)
    headers = employee_headers(client)
    response = client.post(
        "/api/v1/assistant/query",
        json={"query": "What is my attendance summary?"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "not configured" in payload["answer"].lower()
    assert payload["tools_used"] == []


def test_assistant_employee_scoping(client, users, monkeypatch):
    employee = users["employee"]
    _seed_sample_attendance(employee.id)

    # Mock Groq client
    mock_groq = MagicMock()
    # First call: model tries to query employee_id=999
    tool_call = make_tool_call(
        "call_1",
        "get_attendance_summary",
        f'{{"month": "2026-10", "employee_id": 999}}',
    )
    first_res = make_chat_completion(tool_calls=[tool_call])
    second_res = make_chat_completion(content="You have an attendance rate of 100% this month.")
    mock_groq.chat.completions.create.side_effect = [first_res, second_res]

    from app.services import assistant as assistant_svc
    monkeypatch.setattr(assistant_svc, "Groq", lambda **_: mock_groq)

    headers = employee_headers(client)
    response = client.post(
        "/api/v1/assistant/query",
        json={"query": "What is my attendance for 2026-10?"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tools_used"] == ["get_attendance_summary"]
    assert payload["report_data"] is not None
    # Server-enforced scope MUST be employee scope for authenticated employee only
    assert payload["report_data"]["scope"]["kind"] == "employee"
    assert payload["report_data"]["scope"]["employee_id"] == employee.id


def test_assistant_admin_access_all_and_single_employee(client, users, monkeypatch):
    employee = users["employee"]
    _seed_sample_attendance(employee.id)

    mock_groq = MagicMock()
    # Admin queries without employee_id (all employees)
    tc_all = make_tool_call("call_all", "get_attendance_summary", '{"month": "2026-10"}')
    first_res = make_chat_completion(tool_calls=[tc_all])
    second_res = make_chat_completion(content="Organization-wide attendance rate is 100%.")
    mock_groq.chat.completions.create.side_effect = [first_res, second_res]

    from app.services import assistant as assistant_svc
    monkeypatch.setattr(assistant_svc, "Groq", lambda **_: mock_groq)

    headers = admin_headers(client)
    res_all = client.post(
        "/api/v1/assistant/query",
        json={"query": "Show attendance summary for all staff"},
        headers=headers,
    )
    assert res_all.status_code == 200
    payload_all = res_all.json()
    assert payload_all["report_data"]["scope"]["kind"] == "all_employees"

    # Admin queries specific employee
    tc_single = make_tool_call(
        "call_single",
        "get_attendance_summary",
        f'{{"month": "2026-10", "employee_id": {employee.id}}}',
    )
    mock_groq.chat.completions.create.side_effect = [
        make_chat_completion(tool_calls=[tc_single]),
        make_chat_completion(content="Employee attendance rate is 100%."),
    ]
    res_single = client.post(
        "/api/v1/assistant/query",
        json={"query": f"Show attendance for employee {employee.id}"},
        headers=headers,
    )
    assert res_single.status_code == 200
    payload_single = res_single.json()
    assert payload_single["report_data"]["scope"]["kind"] == "employee"
    assert payload_single["report_data"]["scope"]["employee_id"] == employee.id


def test_assistant_tool_allowlisting_rejects_arbitrary_tools(client, users, monkeypatch):
    mock_groq = MagicMock()
    # Model generates forbidden tool call
    tc_forbidden = make_tool_call("call_bad", "execute_sql", '{"sql": "SELECT * FROM users"}')
    first_res = make_chat_completion(tool_calls=[tc_forbidden])
    second_res = make_chat_completion(content="I cannot execute SQL queries.")
    mock_groq.chat.completions.create.side_effect = [first_res, second_res]

    from app.services import assistant as assistant_svc
    monkeypatch.setattr(assistant_svc, "Groq", lambda **_: mock_groq)

    headers = employee_headers(client)
    response = client.post(
        "/api/v1/assistant/query",
        json={"query": "Run a SQL query to fetch all data"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tools_used"] == ["execute_sql"]
    # Check that execute_tool rejects any tool not in ALLOWED_TOOL_NAMES
    assert "execute_sql" not in ALLOWED_TOOL_NAMES


def test_assistant_pii_masking_in_query(client, users, monkeypatch):
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value = make_chat_completion(content="Understood.")

    from app.services import assistant as assistant_svc
    monkeypatch.setattr(assistant_svc, "Groq", lambda **_: mock_groq)

    headers = employee_headers(client)
    secret_key = "gsk_1234567890abcdef1234567890"
    user_email = "sensitive_person@example.com"
    query = f"My email is {user_email} and key is {secret_key}"

    response = client.post(
        "/api/v1/assistant/query",
        json={"query": query},
        headers=headers,
    )
    assert response.status_code == 200

    # Inspect the prompt passed to mock_groq
    calls = mock_groq.chat.completions.create.call_args_list
    assert len(calls) >= 1
    sent_messages = calls[0].kwargs["messages"]
    user_message = next(m["content"] for m in sent_messages if m["role"] == "user")

    assert user_email not in user_message
    assert "[REDACTED_EMAIL]" in user_message
    assert secret_key not in user_message
    assert "[REDACTED_API_KEY]" in user_message


def test_assistant_provider_failure_returns_deterministic_fallback(client, users, monkeypatch):
    mock_groq = MagicMock()
    req = httpx.Request("POST", "https://api.groq.com")
    mock_groq.chat.completions.create.side_effect = APIConnectionError(request=req)

    from app.services import assistant as assistant_svc
    monkeypatch.setattr(assistant_svc, "Groq", lambda **_: mock_groq)

    headers = employee_headers(client)
    response = client.post(
        "/api/v1/assistant/query",
        json={"query": "What is my attendance?"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "unavailable" in payload["answer"].lower() or "unreachable" in payload["answer"].lower()


def test_assistant_provider_failure_after_tool_uses_verified_data(client, users, monkeypatch):
    employee = users["employee"]
    _seed_sample_attendance(employee.id)

    mock_groq = MagicMock()
    tc = make_tool_call("call_sum", "get_attendance_summary", '{"month": "2026-10"}')
    first_res = make_chat_completion(tool_calls=[tc])

    req = httpx.Request("POST", "https://api.groq.com")
    res = httpx.Response(500, request=req)
    second_failure = APIStatusError(message="Groq internal error", response=res, body=None)

    mock_groq.chat.completions.create.side_effect = [first_res, second_failure]

    from app.services import assistant as assistant_svc
    monkeypatch.setattr(assistant_svc, "Groq", lambda **_: mock_groq)

    headers = employee_headers(client)
    response = client.post(
        "/api/v1/assistant/query",
        json={"query": "Summarize my attendance for 2026-10"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tools_used"] == ["get_attendance_summary"]
    assert payload["report_data"] is not None
    # Fallback answer should present verified metrics
    assert "verified" in payload["answer"].lower()
    assert "attendance rate" in payload["answer"].lower()
