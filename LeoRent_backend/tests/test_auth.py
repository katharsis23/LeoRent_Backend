import pytest
import uuid


@pytest.fixture
def signup_payload():
    unique_id = str(uuid.uuid4())[:8]
    # Simple way to get a unique numeric string for phone
    unique_num = int(uuid.uuid4().int % 100000000)
    return {
        "email": f"test_{unique_id}@example.com",
        "username": f"user_{unique_id}",
        "phone": f"+38050{unique_num:08d}",
        "password": "password123",
        "user_type": "default",
    }


@pytest.fixture
def login_payload():
    return {
        "email": "test@example.com",
        "password": "password123",
    }


def test_signup_v1_creates_user(client, signup_payload):
    response = client.post("/users/signup/v1", json=signup_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == signup_payload["email"]
    assert body["username"] == signup_payload["username"]
    assert body["phone"] == signup_payload["phone"]
    assert "id" in body


def test_signup_v1_duplicate_email_rejected(client, signup_payload):
    response1 = client.post("/users/signup/v1", json=signup_payload)
    assert response1.status_code == 201

    response2 = client.post("/users/signup/v1", json=signup_payload)
    assert response2.status_code == 400


def test_login_v1_success(client, signup_payload, login_payload):
    # Need to use the same email for both
    login_payload["email"] = signup_payload["email"]
    
    response1 = client.post("/users/signup/v1", json=signup_payload)
    assert response1.status_code == 201

    response2 = client.post("/users/login/v1", json=login_payload)
    assert response2.status_code == 200
    body = response2.json()
    assert body["email"] == login_payload["email"]
    assert "id" in body


def test_login_v1_wrong_password_fails(client, signup_payload):
    response1 = client.post("/users/signup/v1", json=signup_payload)
    assert response1.status_code == 201

    response2 = client.post(
        "/users/login/v1",
        json={"email": signup_payload["email"], "password": "wrong"},
    )
    assert response2.status_code == 400
