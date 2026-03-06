import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"

from app.api.deps import get_db  # noqa: E402
from app.db.database import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402


TEST_ENGINE = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False}, future=True)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False, future=True)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_user(db: Session) -> User:
    admin = User(
        name="Admin",
        email="admin@test.local",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture()
def normal_user(db: Session) -> User:
    user = User(
        name="User",
        email="user@test.local",
        password_hash=get_password_hash("user123"),
        role=UserRole.USER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
