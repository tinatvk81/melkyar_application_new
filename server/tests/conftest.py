"""
زیرساخت تست‌ها. نکته‌ی مهم: این تست‌ها روی یک دیتابیس PostgreSQL واقعیِ جدا
(نه SQLite) اجرا می‌شوند، چون کد از قابلیت‌های مخصوص پستگرس (JSONB، ILIKE
روی چند ستون، Enum) استفاده می‌کند که در SQLite رفتار یکسانی ندارند — تستی که
روی SQLite «سبز» شود ولی روی پستگرس واقعی خراب باشد، ارزشی ندارد.

قبل از اجرای تست‌ها، یک دیتابیس با نام realestate_test باید وجود داشته باشد:
    CREATE DATABASE realestate_test OWNER realestate_app;
(یا هر نام دیگری که در متغیر محیطی TEST_POSTGRES_DB مشخص کنید)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import user, property, property_image, activity_log  # noqa: register all models
from app.models.user import User, UserRole
from app.core.security import hash_password

TEST_DB_NAME = os.environ.get("TEST_POSTGRES_DB", settings.POSTGRES_DB + "_test")
TEST_DATABASE_URL = (
    f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{TEST_DB_NAME}"
)

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """یک‌بار در ابتدای کل مجموعه‌ی تست‌ها: همه‌ی جدول‌ها را می‌سازد."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """بین هر تست: همه‌ی جدول‌ها را خالی می‌کند تا تست‌ها روی هم اثر نگذارند."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))


@pytest.fixture
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db_session, username, password, role, full_name=None):
    u = User(
        username=username,
        full_name=full_name or username,
        hashed_password=hash_password(password),
        role=role,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def admin_user(db_session):
    return _create_user(db_session, "test_admin", "adminpass123", UserRole.admin, "مدیر تست")


@pytest.fixture
def agent_user(db_session):
    return _create_user(db_session, "test_agent1", "agentpass123", UserRole.agent, "مشاور یک")


@pytest.fixture
def agent2_user(db_session):
    return _create_user(db_session, "test_agent2", "agentpass123", UserRole.agent, "مشاور دو")


def _login(client, username, password) -> str:
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def admin_token(client, admin_user):
    return _login(client, "test_admin", "adminpass123")


@pytest.fixture
def agent_token(client, agent_user):
    return _login(client, "test_agent1", "agentpass123")


@pytest.fixture
def agent2_token(client, agent2_user):
    return _login(client, "test_agent2", "agentpass123")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
