import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.leorent_backend.main import app
from src.leorent_backend.database_connector import get_db, AsyncSessionLocal


@pytest.fixture(scope="function")
def client():
    """Test client with overridden DB dependency."""
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def firebase_token():
    """Mock Firebase token for testing."""
    return "mock_firebase_token_12345"


@pytest.fixture
def firebase_decoded_token():
    """Mock decoded Firebase token."""
    return {
        'uid': 'firebase_uid_12345',
        'email': 'firebase@example.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '+1234567890',
        'email_verified': True
    }


class TestFirebaseAuth:
    """Test Firebase authentication endpoints."""

    @patch('src.leorent_backend.external.firebase_client.firebase_app')
    @patch('firebase_admin.auth.verify_id_token')
    def test_firebase_auth_success(
        self, mock_verify, mock_firebase_app,
        client, firebase_token, firebase_decoded_token
    ):
        """Test successful Firebase authentication."""
        # Setup mocks
        mock_firebase_app.return_value = MagicMock()
        mock_verify.return_value = firebase_decoded_token

        response = client.post(
            "/users/firebase-auth/v1",
            json={
                "id_token": firebase_token,
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1234567890",
                "user_type": "AGENT"
            }
        )

        if response.status_code != 200:
            print(f"Error Response: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == firebase_decoded_token["email"]
        assert data["firebase_uid"] == firebase_decoded_token["uid"]
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["user_type"] == "AGENT"
        assert "id" in data

    @patch('src.leorent_backend.external.firebase_client.firebase_app')
    @patch('firebase_admin.auth.verify_id_token')
    def test_firebase_auth_invalid_token(
            self, mock_verify, mock_firebase_app, client):
        """Test Firebase authentication with invalid token."""
        # Setup mocks
        mock_firebase_app.return_value = MagicMock()
        from firebase_admin import auth
        mock_verify.side_effect = auth.InvalidIdTokenError("Invalid token")

        response = client.post(
            "/users/firebase-auth/v1",
            json={
                "id_token": "invalid_token",
                "first_name": "X",
                "last_name": "Y",
                "phone": "+1234567890",
                "user_type": "DEFAULT"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @patch('src.leorent_backend.external.firebase_client.firebase_app')
    @patch('firebase_admin.auth.verify_id_token')
    def test_firebase_auth_no_token(
            self,
            mock_verify,
            mock_firebase_app,
            client):
        """Test Firebase authentication without token."""
        # Setup mocks
        mock_firebase_app.return_value = MagicMock()

        response = client.post(
            "/users/firebase-auth/v1",
            json={}
        )

        assert response.status_code == 422  # Validation error


class TestFirebaseRouter:
    """Test Firebase router endpoints."""

    @patch('src.leorent_backend.external.firebase_client.firebase_app')
    @patch('firebase_admin.auth.verify_id_token')
    def test_firebase_signup_success(
        self, mock_verify, mock_firebase_app,
        client, firebase_token, firebase_decoded_token
    ):
        """Test successful Firebase signup."""
        # Setup mocks
        mock_firebase_app.return_value = MagicMock()
        mock_verify.return_value = firebase_decoded_token

        response = client.post(
            "/firebase/signup",
            headers={"Authorization": f"Bearer {firebase_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Firebase user authenticated successfully"
        assert "user" in data
        assert data["user"]["email"] == firebase_decoded_token["email"]

    @patch('src.leorent_backend.external.firebase_client.firebase_app')
    @patch('firebase_admin.auth.verify_id_token')
    def test_firebase_me_success(
        self, mock_verify, mock_firebase_app,
        client, firebase_token, firebase_decoded_token
    ):
        """Test getting current Firebase user profile."""
        # Setup mocks
        mock_firebase_app.return_value = MagicMock()
        mock_verify.return_value = firebase_decoded_token

        response = client.get(
            "/firebase/me",
            headers={"Authorization": f"Bearer {firebase_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == firebase_decoded_token["email"]

    def test_firebase_endpoints_no_token(self, client):
        """Test Firebase endpoints without authorization header."""
        # Test signup without token
        response = client.post("/firebase/signup")
        assert response.status_code == 401

        # Test me without token
        response = client.get("/firebase/me")
        assert response.status_code == 401
