from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.audit import AuditLog


def login(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health_and_readiness(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_login_returns_jwt_and_me_is_scoped_to_token_user(client, users):
    token = login(client, "ADMIN@EXAMPLE.COM", "admin-password")

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
    assert response.json()["role"] == "admin"

    with SessionLocal() as db:
        event = db.scalar(select(AuditLog).where(AuditLog.action == "auth.login_succeeded"))
        assert event is not None
        assert event.actor_user_id == users["admin"].id
        assert event.metadata_json == {"role": "admin"}


def test_invalid_credentials_are_rejected_without_account_enumeration(client, users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "invalid_credentials", "message": "Email or password is incorrect."}
    }

    with SessionLocal() as db:
        event = db.scalar(select(AuditLog).where(AuditLog.action == "auth.login_failed"))
        assert event is not None
        assert event.metadata_json == {"reason": "invalid_credentials"}


def test_protected_endpoint_requires_a_bearer_token(client, users):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_admin_endpoint_rejects_employee_and_allows_admin(client, users):
    employee_token = login(client, "employee@example.com", "employee-password")
    employee_response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert employee_response.status_code == 403
    assert employee_response.json()["error"]["code"] == "forbidden"

    admin_token = login(client, "admin@example.com", "admin-password")
    admin_response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_response.status_code == 200
    assert {user["role"] for user in admin_response.json()} == {"admin", "employee"}


def test_validation_errors_use_consistent_shape(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert len(response.json()["error"]["details"]) == 2
