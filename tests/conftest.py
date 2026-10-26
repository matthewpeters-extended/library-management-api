import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.limiter import limiter
from app.main import app
from app.models import Author, User, UserRole
from app.security import hash_password

# The /login rate limit is for real-world abuse prevention; it would otherwise
# fire mid-suite since slowapi keys by client IP and the test client always
# looks like the same IP.
limiter.enabled = False

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_user(db_session, name, email, password, role):
    user = User(name=name, email=email, password=hash_password(password), role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, email, password):
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def admin_user(db_session):
    return _make_user(db_session, "Admin", "admin@test-suite.dev", "admin123", UserRole.admin)


@pytest.fixture()
def librarian_user(db_session):
    return _make_user(
        db_session, "Librarian", "librarian@test-suite.dev", "lib12345", UserRole.librarian
    )


@pytest.fixture()
def member_user(db_session):
    return _make_user(db_session, "Member", "member@test-suite.dev", "member123", UserRole.member)


@pytest.fixture()
def admin_token(client, admin_user):
    return _login(client, "admin@test-suite.dev", "admin123")


@pytest.fixture()
def librarian_token(client, librarian_user):
    return _login(client, "librarian@test-suite.dev", "lib12345")


@pytest.fixture()
def member_token(client, member_user):
    return _login(client, "member@test-suite.dev", "member123")


@pytest.fixture()
def auth_header():
    def _header(token):
        return {"Authorization": f"Bearer {token}"}

    return _header


@pytest.fixture()
def author(db_session):
    a = Author(name="Test Author")
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a
