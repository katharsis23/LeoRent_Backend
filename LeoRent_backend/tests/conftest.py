import pytest
from fastapi.testclient import TestClient
from src.leorent_backend.main import app
from src.leorent_backend.database_connector import get_db, AsyncSessionLocal, engine
from src.leorent_backend.external.firebase_auth import get_current_user
from src.leorent_backend.models import Users, UserType
from uuid import uuid4
import asyncio


@pytest.fixture(scope="function")
async def db_session():
    """Database session fixture for tests."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def client():
    """Test client with overridden DB dependency and mocked authentication."""

    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    # Mock Firebase authentication with a test user
    def mock_get_current_user():
        return Users(
            id_=uuid4(),
            email="test_user@example.com",
            firebase_uid="test_uid_12345",
            first_name="Test",
            last_name="User",
            phone_number="+1234567890",
            type_=UserType.OWNER,
            is_verified=True
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

    # Clear the engine pool to avoid loop mismatch in next test
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(engine.dispose())
        else:
            loop.run_until_complete(engine.dispose())
    except Exception:
        # Fallback for complex loop scenarios
        pass


@pytest.fixture(scope="function")
def client_without_auth():
    """Test client without authentication override for testing unauthorized access."""

    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # Don't override get_current_user to test real authentication

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

    # Clear the engine pool to avoid loop mismatch in next test
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(engine.dispose())
        else:
            loop.run_until_complete(engine.dispose())
    except Exception:
        # Fallback for complex loop scenarios
        pass


# --- New Fixtures ---

@pytest.fixture
def jwt_token():
    """Return a fake JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzNDUifQ.mock_signature"


@pytest.fixture
def auth_headers(jwt_token):
    """Return auth headers."""
    return {"Authorization": f"Bearer {jwt_token}"}
