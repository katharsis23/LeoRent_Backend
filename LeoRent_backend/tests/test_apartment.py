import pytest
import random
from uuid import UUID as PythonUUID

from src.leorent_backend.models import Users, UserType
from src.leorent_backend.main import app
from src.leorent_backend.external.firebase_auth import get_current_user


@pytest.fixture
def seeded_owner(client):
    """
    Seed an owner user via the API and return the user object.
    This is fully synchronous and ensures the user exists for ForeignKeys.
    """
    user_data = {
        "username": f"owner_{random.randint(10000, 999999)}",
        "password": "testpassword123",
        "email": f"owner_{random.randint(10000, 999999)}@example.com",
        "phone": f"+38099{random.randint(1000000, 9999999)}",
        "user_type": "owner"
    }

    # Create user
    resp = client.post("/users/signup/v1", json=user_data)
    if resp.status_code != 201:
        print(f"Response status: {resp.status_code}")
        print(f"Response body: {resp.text}")
    assert resp.status_code == 201

    # Get user object
    user = Users(
        id_=PythonUUID(resp.json()["id"]),
        username=user_data["username"],
        password="hashed",  # Not relevant for tests
        email=user_data["email"],
        type_=UserType.OWNER,
        phone_number=user_data["phone"],
        is_verified=False,
        firebase_uid=None,
        first_name=None,
        last_name=None
    )

    return user


@pytest.fixture
def seeded_user(client):
    """
    Seed a regular user via the API and return the user object.
    This is fully synchronous and ensures the user exists for testing likes.
    """
    user_data = {
        "username": f"user_{random.randint(10000, 999999)}",
        "password": "testpassword123",
        "email": f"user_{random.randint(10000, 999999)}@example.com",
        "phone": f"+38099{random.randint(1000000, 9999999)}",
        "user_type": "agent"
    }

    # Create user
    resp = client.post("/users/signup/v1", json=user_data)
    assert resp.status_code == 201

    # Get user object
    user = Users(
        id_=PythonUUID(resp.json()["id"]),
        username=user_data["username"],
        password="hashed",  # Not relevant for tests
        email=user_data["email"],
        type_=UserType.AGENT,  # Use Enum to match router check
        phone_number=user_data["phone"],
        is_verified=False,
        firebase_uid=None,
        first_name=None,
        last_name=None
    )

    return user


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
    assert "apartments" in response.json()
    assert isinstance(response.json()["apartments"], list)


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
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

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
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    # Delete
    assert client.delete(f"/apartment/{apt_id}", headers=auth_headers_new).status_code == 204

    # Verify
    assert client.get(f"/apartment/{apt_id}", headers=auth_headers_new).status_code == 404


def test_get_my_apartments(client, auth_headers_new, seeded_owner):
    """Test GET /apartment/my/ - get current user's apartments."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    # Create some apartments for the user
    apt1_data = {
        "title": "My Apt 1", "location": "L1", "district": "D1", "cost": 100,
        "rent_type": "DEFAULT", "rooms": 1, "square": 10.0, "floor": 1,
        "floor_in_house": 1, "type_": "brick", "renovation_type": "none"
    }
    apt2_data = {
        "title": "My Apt 2", "location": "L2", "district": "D2", "cost": 200,
        "rent_type": "DEFAULT", "rooms": 2, "square": 20.0, "floor": 2,
        "floor_in_house": 2, "type_": "panel", "renovation_type": "cosmetic"
    }

    resp1 = client.post("/apartment/", json=apt1_data, headers=auth_headers_new)
    assert resp1.status_code == 201
    resp2 = client.post("/apartment/", json=apt2_data, headers=auth_headers_new)
    assert resp2.status_code == 201

    # Get my apartments
    resp = client.get("/apartment/my/", headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert "apartments" in data
    assert len(data["apartments"]) == 2

    # Verify apartment data
    titles = [apt["title"] for apt in data["apartments"]]
    assert "My Apt 1" in titles
    assert "My Apt 2" in titles


def test_get_my_apartments_empty(client, auth_headers_new, seeded_owner):
    """Test GET /apartment/my/ when user has no apartments."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    resp = client.get("/apartment/my/", headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert "apartments" in data
    assert len(data["apartments"]) == 0


def test_get_my_apartments_pagination(client, auth_headers_new, seeded_owner):
    """Test GET /apartment/my/ with pagination."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    # Create 3 apartments
    for i in range(3):
        apt_data = {
            "title": f"My Apt {i+1}", "location": f"L{i+1}", "district": f"D{i+1}",
            "cost": 100 + i*50, "rent_type": "DEFAULT", "rooms": 1, "square": 10.0,
            "floor": 1, "floor_in_house": 1, "type_": "brick", "renovation_type": "none"
        }
        resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
        assert resp.status_code == 201

    # Test first page with page_size=2
    resp = client.get("/apartment/my/?current_page=1&page_size=2", headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["apartments"]) == 2

    # Test second page
    resp = client.get("/apartment/my/?current_page=2&page_size=2", headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["apartments"]) == 1


def test_like_apartment(client, auth_headers_new, seeded_owner, seeded_user):
    """Test POST /apartment/{apartment_id}/like - toggle like functionality."""

    # Create an apartment as owner (using seeded_owner, not seeded_user)
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apt_data = {
        "title": "Apartment to Like", "location": "L", "district": "D", "cost": 100,
        "rent_type": "DEFAULT", "rooms": 1, "square": 10.0, "floor": 1,
        "floor_in_house": 1, "type_": "brick", "renovation_type": "none"
    }
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    # Switch to regular user to like apartment
    app.dependency_overrides[get_current_user] = lambda: seeded_user

    # Like apartment
    resp1 = client.post(f"/apartment/{apt_id}/like", headers=auth_headers_new)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "liked"
    assert data1["message"] == "Apartment liked successfully"

    # Unlike apartment (toggle again)
    resp2 = client.post(f"/apartment/{apt_id}/like", headers=auth_headers_new)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "unliked"
    assert data2["message"] == "Apartment unliked successfully"


def test_like_nonexistent_apartment(client, auth_headers_new, seeded_user):
    """Test liking a non-existent apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_user

    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(f"/apartment/{fake_id}/like", headers=auth_headers_new)
    assert resp.status_code == 404  # Should return 404 for non-existent apartment


def test_get_liked_apartments(client, auth_headers_new, seeded_owner, seeded_user):
    """Test GET /apartment/liked/ - get liked apartments."""
    # Create apartments as owner
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apt1_data = {
        "title": "Apartment 1", "location": "L1", "district": "D1", "cost": 100,
        "rent_type": "DEFAULT", "rooms": 1, "square": 10.0, "floor": 1,
        "floor_in_house": 1, "type_": "brick", "renovation_type": "none"
    }
    apt2_data = {
        "title": "Apartment 2", "location": "L2", "district": "D2", "cost": 200,
        "rent_type": "DEFAULT", "rooms": 2, "square": 20.0, "floor": 2,
        "floor_in_house": 2, "type_": "panel", "renovation_type": "cosmetic"
    }

    apt1_id = client.post("/apartment/", json=apt1_data, headers=auth_headers_new).json()["id_"]
    apt2_id = client.post("/apartment/", json=apt2_data, headers=auth_headers_new).json()["id_"]

    # Switch to regular user to like both apartments
    app.dependency_overrides[get_current_user] = lambda: seeded_user

    # Like both apartments
    client.post(f"/apartment/{apt1_id}/like", headers=auth_headers_new)
    client.post(f"/apartment/{apt2_id}/like", headers=auth_headers_new)

    # Get liked apartments
    resp = client.get("/apartment/liked/", headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert "apartments" in data
    assert len(data["apartments"]) == 2

    # Verify apartment data
    titles = [apt["title"] for apt in data["apartments"]]
    assert "Apartment 1" in titles
    assert "Apartment 2" in titles


def test_get_liked_apartments_empty(client, auth_headers_new, seeded_user):
    """Test GET /apartment/liked/ when user hasn't liked any apartments."""
    app.dependency_overrides[get_current_user] = lambda: seeded_user

    resp = client.get("/apartment/liked/", headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert "apartments" in data
    assert len(data["apartments"]) == 0


def test_like_and_get_liked_workflow(client, auth_headers_new, seeded_owner, seeded_user):
    """Test complete workflow: create apartments, toggle like, get liked list."""
    # Switch to owner to create apartments
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    # Create 2 apartments
    apt1_data = {
        "title": "Cozy Apartment", "location": "Center", "district": "Downtown",
        "cost": 150, "rent_type": "DEFAULT", "rooms": 1, "square": 25.0,
        "floor": 3, "floor_in_house": 5, "type_": "brick", "renovation_type": "euro"
    }
    apt2_data = {
        "title": "Luxury Apartment", "location": "Premium", "district": "Uptown",
        "cost": 500, "rent_type": "DAILY", "rooms": 3, "square": 80.0,
        "floor": 10, "floor_in_house": 15, "type_": "monolith", "renovation_type": "euro"
    }

    apt1_id = client.post("/apartment/", json=apt1_data, headers=auth_headers_new).json()["id_"]
    apt2_id = client.post("/apartment/", json=apt2_data, headers=auth_headers_new).json()["id_"]

    # Switch to regular user to like apartments
    app.dependency_overrides[get_current_user] = lambda: seeded_user

    # Like first apartment
    resp1 = client.post(f"/apartment/{apt1_id}/like", headers=auth_headers_new)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "liked"

    # Check liked apartments - should have 1
    resp = client.get("/apartment/liked/", headers=auth_headers_new)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["apartments"]) == 1
    assert data["apartments"][0]["title"] == "Cozy Apartment"

    # Like second apartment
    resp2 = client.post(f"/apartment/{apt2_id}/like", headers=auth_headers_new)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "liked"

    # Check liked apartments - should have 2
    resp = client.get("/apartment/liked/", headers=auth_headers_new)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["apartments"]) == 2

    # Verify both apartments are in liked list
    titles = [apt["title"] for apt in data["apartments"]]
    assert "Cozy Apartment" in titles
    assert "Luxury Apartment" in titles

    # Unlike first apartment
    resp3 = client.post(f"/apartment/{apt1_id}/like", headers=auth_headers_new)
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["status"] == "unliked"

    # Check liked apartments - should have 1 again
    resp = client.get("/apartment/liked/", headers=auth_headers_new)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["apartments"]) == 1
    assert data["apartments"][0]["title"] == "Luxury Apartment"
