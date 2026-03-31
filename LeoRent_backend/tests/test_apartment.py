import pytest
from uuid import UUID
from src.leorent_backend.models import Users, UserType
from src.leorent_backend.main import app
from src.leorent_backend.external.firebase_auth import get_current_user


@pytest.fixture
def seeded_owner(client):
    """
    Seed an owner user via the API and return the user object.
    This is fully synchronous and ensures the user exists for ForeignKeys.
    """
    import random
    unique_email = f"owner_{random.randint(1000, 9999)}@example.com"
    signup_data = {
        "email": unique_email,
        "username": f"user_{random.randint(1000, 9999)}",
        "phone": f"+38099{random.randint(1000000, 9999999)}",
        "password": "password123",
        "user_type": "owner"
    }
    resp = client.post("/users/signup/v1", json=signup_data)
    assert resp.status_code == 201
    user_data = resp.json()

    # Return a Users object that matches what was created
    return Users(
        id_=UUID(user_data["id"]),
        email=user_data["email"],
        username=user_data["username"],
        phone_number=user_data["phone"],
        type_=UserType.OWNER,
        is_verified=True
    )


@pytest.fixture
def auth_headers_new():
    """Return auth headers."""
    return {"Authorization": "Bearer some_dummy_token"}


def test_get_all_apartments_empty(client, auth_headers_new, seeded_owner):
    """Test GET all apartments when empty."""
    # Override for this specific test
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    response = client.get("/apartment/", headers=auth_headers_new)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_and_get_apartment(client, auth_headers_new, seeded_owner):
    """Test POST create and then GET that apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apartment_data = {
        "title": "Sync Test Apartment",
        "description": "Created in a synchronous test",
        "location": "Loc",
        "district": "Dist",
        "cost": 2000,
        "rent_type": "DEFAULT",
        "rooms": 3,
        "square": 80.0,
        "floor": 10,
        "floor_in_house": 20,
        "type_": "monolith",
        "renovation_type": "euro"
    }

    # 1. Create
    resp = client.post("/apartment/", headers=auth_headers_new, json=apartment_data)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    # 2. Get
    resp = client.get(f"/apartment/{apt_id}", headers=auth_headers_new)
    assert resp.status_code == 200
    assert resp.json()["title"] == apartment_data["title"]


def test_update_apartment(client, auth_headers_new, seeded_owner):
    """Test PUT update apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    # Create first
    apt_data = {
        "title": "Initial", "location": "L", "district": "D", "cost": 100,
        "rent_type": "DEFAULT", "rooms": 1, "square": 10.0, "floor": 1,
        "floor_in_house": 1, "type_": "brick", "renovation_type": "none"
    }
    apt_id = client.post("/apartment/", json=apt_data, headers=auth_headers_new).json()["id_"]

    # Update
    update_data = {"title": "Updated", "cost": 150}
    resp = client.put(f"/apartment/{apt_id}", json=update_data, headers=auth_headers_new)
    assert resp.status_code == 200

    # Verify
    assert client.get(f"/apartment/{apt_id}", headers=auth_headers_new).json()["title"] == "Updated"


def test_delete_apartment(client, auth_headers_new, seeded_owner):
    """Test DELETE apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    # Create
    apt_data = {
        "title": "Del", "location": "L", "district": "D", "cost": 100,
        "rent_type": "DEFAULT", "rooms": 1, "square": 10.0, "floor": 1,
        "floor_in_house": 1, "type_": "brick", "renovation_type": "none"
    }
    apt_id = client.post("/apartment/", json=apt_data, headers=auth_headers_new).json()["id_"]

    # Delete
    assert client.delete(f"/apartment/{apt_id}", headers=auth_headers_new).status_code == 204

    # Verify
    assert client.get(f"/apartment/{apt_id}", headers=auth_headers_new).status_code == 404
