from datetime import datetime, timezone
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_attendance.db")

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db
from app.main import app
from app.models.user import User, UserRole
from app.core.security import hash_password


@pytest.fixture(autouse=True)
def clean_database():
    from app.models.shift import Shift
    Shift._working_days_registry.clear()
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Shift._working_days_registry.clear()


@pytest.fixture
def users():
    with SessionLocal() as db:
        admin = User(
            email="admin@example.com",
            full_name="Admin User",
            password_hash=hash_password("admin-password"),
            role=UserRole.ADMIN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        employee = User(
            email="employee@example.com",
            full_name="Employee User",
            password_hash=hash_password("employee-password"),
            role=UserRole.EMPLOYEE,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db.add_all([admin, employee])
        db.commit()
        db.refresh(admin)
        db.refresh(employee)
        return {"admin": admin, "employee": employee}


@pytest.fixture
def client():
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
