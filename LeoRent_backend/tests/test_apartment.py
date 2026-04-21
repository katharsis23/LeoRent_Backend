import json
import pytest
import random
from unittest.mock import AsyncMock, patch
from uuid import UUID as PythonUUID

from src.leorent_backend.models import Users, UserType
from src.leorent_backend.main import app
from src.leorent_backend.external.firebase_auth import get_current_user, get_optional_user


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
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

    response = client.get("/apartment/", headers=auth_headers_new)
    assert response.status_code == 200
    assert "apartments" in response.json()
    assert isinstance(response.json()["apartments"], list)


def test_create_and_get_apartment(client, auth_headers_new, seeded_owner):
    """Test POST create and then GET that apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

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
    resp = client.post(
        "/apartment/",
        headers=auth_headers_new,
        json=apartment_data)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    # 2. Get
    resp = client.get(f"/apartment/{apt_id}", headers=auth_headers_new)
    assert resp.status_code == 200
    assert resp.json()["title"] == apartment_data["title"]


def test_create_apartment_uploads_main_picture_to_backblaze(
    client, auth_headers_new, seeded_owner
):
    """Main picture sources should be uploaded before saving apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

    apartment_data = {
        "title": "Apartment with main photo",
        "description": "Created with image sync",
        "location": "Kyiv",
        "district": "Center",
        "cost": 27000,
        "rent_type": "DEFAULT",
        "rooms": 2,
        "square": 70.0,
        "floor": 5,
        "floor_in_house": 12,
        "details": {"wifi": True},
        "type_": "brick",
        "renovation_type": "euro",
        "main_pictures": "https://cdn.example.com/apartment-main.jpg"
    }

    with patch(
        "src.leorent_backend.services.backblaze_service."
        "backblaze_service.upload_photo_from_source_details",
        new_callable=AsyncMock,
    ) as mock_upload:
        mock_upload.return_value = {
            "url": (
                "https://s3.eu-central-003.backblazeb2.com/"
                "leorent-photos/apartments/main.jpg"
            ),
            "content_type": "image/jpeg",
            "size_bytes": 12345,
        }

        resp = client.post(
            "/apartment/", headers=auth_headers_new, json=apartment_data
        )

    assert resp.status_code == 201
    apt_id = resp.json()["id_"]
    mock_upload.assert_awaited_once()

    resp = client.get(f"/apartment/{apt_id}", headers=auth_headers_new)
    assert resp.status_code == 200
    assert resp.json()["main_pictures"] == [
        "https://s3.eu-central-003.backblazeb2.com/"
        "leorent-photos/apartments/main.jpg"
    ]
    assert resp.json()["pictures"] == []


def test_create_apartment_accepts_local_picture_upload(
    client, auth_headers_new, seeded_owner
):
    """Local file uploads should also be stored in Backblaze."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    with patch(
        "src.leorent_backend.services.backblaze_service."
        "backblaze_service.upload_photo_from_bytes",
        new_callable=AsyncMock,
    ) as mock_upload:
        mock_upload.return_value = (
            "https://s3.eu-central-003.backblazeb2.com/"
            "leorent-photos/apartments/local-main.jpg"
        )

        resp = client.post(
            "/apartment/",
            headers=auth_headers_new,
            data={
                "title": "Apartment with local file",
                "description": "Created from multipart form",
                "location": "Kyiv",
                "district": "Center",
                "cost": "19500",
                "rent_type": "DEFAULT",
                "rooms": "2",
                "square": "58.0",
                "floor": "4",
                "floor_in_house": "10",
                "details": '{"wifi": true}',
                "type_": "brick",
                "renovation_type": "euro",
            },
            files={
                "main_pictures_files": (
                    "main.jpg",
                    b"fake-image-bytes",
                    "image/jpeg",
                )
            },
        )

    assert resp.status_code == 201
    assert resp.json()["main_pictures"] == [
        "https://s3.eu-central-003.backblazeb2.com/"
        "leorent-photos/apartments/local-main.jpg"
    ]
    assert resp.json()["pictures"] == []
    mock_upload.assert_awaited_once()


def test_update_apartment(client, auth_headers_new, seeded_owner):
    """Test PUT update apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

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
    resp = client.put(
        f"/apartment/{apt_id}",
        json=update_data,
        headers=auth_headers_new)
    assert resp.status_code == 200

    # Verify
    assert client.get(
        f"/apartment/{apt_id}",
        headers=auth_headers_new).json()["title"] == "Updated"


def test_delete_apartment(client, auth_headers_new, seeded_owner):
    """Test DELETE apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

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
    assert client.delete(
        f"/apartment/{apt_id}",
        headers=auth_headers_new).status_code == 204

    # Verify
    assert client.get(
        f"/apartment/{apt_id}",
        headers=auth_headers_new).status_code == 404


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

    resp1 = client.post(
        "/apartment/",
        json=apt1_data,
        headers=auth_headers_new)
    assert resp1.status_code == 201
    resp2 = client.post(
        "/apartment/",
        json=apt2_data,
        headers=auth_headers_new)
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
            "title": f"My Apt {
                i + 1}",
            "location": f"L{
                i + 1}",
            "district": f"D{
                i + 1}",
            "cost": 100 + i * 50,
            "rent_type": "DEFAULT",
            "rooms": 1,
            "square": 10.0,
            "floor": 1,
            "floor_in_house": 1,
            "type_": "brick",
            "renovation_type": "none"}
        resp = client.post(
            "/apartment/",
            json=apt_data,
            headers=auth_headers_new)
        assert resp.status_code == 201

    # Test first page with page_size=2
    resp = client.get(
        "/apartment/my/?current_page=1&page_size=2",
        headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["apartments"]) == 2

    # Test second page
    resp = client.get(
        "/apartment/my/?current_page=2&page_size=2",
        headers=auth_headers_new)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["apartments"]) == 1


def test_rejects_oversized_main_picture_upload(
    client, auth_headers_new, seeded_owner
):
    """Main picture file larger than 10 MB should be rejected."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    resp = client.post(
        "/apartment/",
        headers=auth_headers_new,
        data={
            "title": "Big image apartment",
            "location": "Kyiv",
            "district": "Center",
            "cost": "10000",
            "rent_type": "DEFAULT",
            "rooms": "1",
            "square": "50.0",
            "floor": "2",
            "floor_in_house": "10",
            "type_": "brick",
            "renovation_type": "euro",
        },
        files={
            "main_pictures_files": (
                "big.jpg",
                b"x" * (10 * 1024 * 1024 + 1),
                "image/jpeg",
            )
        },
    )

    assert resp.status_code == 400
    assert "10 mb" in resp.json()["detail"].lower()


def test_owner_can_add_apartment_pictures_in_single_request(
    client, auth_headers_new, seeded_owner
):
    """Owner can upload multiple apartment pictures with metadata."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apt_data = {
        "title": "Apartment with gallery",
        "location": "L",
        "district": "D",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"
    }
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    metadata = [
        {"room": "kitchen"},
        {"room": "bedroom"},
        {"room": "living"},
        {"room": "balcony"},
    ]

    with patch(
        "src.leorent_backend.services.backblaze_service."
        "backblaze_service.upload_photo_from_source_details",
        new_callable=AsyncMock,
    ) as mock_source_upload, patch(
        "src.leorent_backend.services.backblaze_service."
        "backblaze_service.upload_photo_from_bytes",
        new_callable=AsyncMock,
    ) as mock_file_upload:
        mock_source_upload.side_effect = [
            {
                "url": "https://b2.example/gallery/url-1.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 111,
            },
            {
                "url": "https://b2.example/gallery/url-2.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 222,
            },
        ]
        mock_file_upload.side_effect = [
            "https://b2.example/gallery/file-1.jpg",
            "https://b2.example/gallery/file-2.jpg",
        ]

        resp = client.post(
            f"/apartment/{apt_id}/pictures",
            headers=auth_headers_new,
            files=[
                ("picture_urls", (None, "https://cdn.example.com/1.jpg")),
                ("picture_urls", (None, "https://cdn.example.com/2.jpg")),
                ("metadata", (None, json.dumps(metadata))),
                ("picture_files", ("3.jpg", b"img-3", "image/jpeg")),
                ("picture_files", ("4.jpg", b"img-4", "image/jpeg")),
            ],
        )

    assert resp.status_code == 201
    data = resp.json()
    assert len(data["pictures"]) == 4
    assert data.get("main_pictures", []) == []

    picture_metadata = [picture["metadata"] for picture in data["pictures"]]
    rooms = {metadata["room"] for metadata in picture_metadata}

    assert rooms == {"kitchen", "bedroom", "living", "balcony"}
    assert all(metadata["format"] == "jpg" for metadata in picture_metadata)
    assert all("is_main" not in metadata for metadata in picture_metadata)
    assert {metadata["size_bytes"] for metadata in picture_metadata} == {
        111,
        222,
        len(b"img-3"),
        len(b"img-4"),
    }
    assert mock_source_upload.await_count == 2
    assert mock_file_upload.await_count == 2


def test_non_owner_cannot_add_apartment_pictures(
    client, auth_headers_new, seeded_owner, seeded_user
):
    """Only the apartment owner can add gallery pictures."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apt_data = {
        "title": "Protected apartment",
        "location": "L",
        "district": "D",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"
    }
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    app.dependency_overrides[get_current_user] = lambda: seeded_user
    resp = client.post(
        f"/apartment/{apt_id}/pictures",
        headers=auth_headers_new,
        json={"pictures": [{"source": "https://cdn.example.com/1.jpg"}]},
    )

    assert resp.status_code == 403


def test_rejects_oversized_gallery_picture_upload(
    client, auth_headers_new, seeded_owner
):
    """Gallery picture file larger than 10 MB should be rejected."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apt_data = {
        "title": "Oversized gallery apartment",
        "location": "L",
        "district": "D",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"
    }
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    resp = client.post(
        f"/apartment/{apt_id}/pictures",
        headers=auth_headers_new,
        files=[
            (
                "picture_files",
                (
                    "too-big.jpg",
                    b"x" * (10 * 1024 * 1024 + 1),
                    "image/jpeg",
                ),
            )
        ],
    )

    assert resp.status_code == 400
    assert "10 mb" in resp.json()["detail"].lower()


def test_owner_can_soft_delete_single_picture(
    client, auth_headers_new, seeded_owner
):
    """Owner can soft-delete one apartment picture by id."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

    apt_data = {
        "title": "Apartment picture delete",
        "location": "L",
        "district": "D",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"
    }
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    with patch(
        "src.leorent_backend.services.backblaze_service."
        "backblaze_service.upload_photo_from_source_details",
        new_callable=AsyncMock,
    ) as mock_upload:
        mock_upload.return_value = {
            "url": "https://b2.example/gallery/delete-me.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 777,
        }
        resp = client.post(
            f"/apartment/{apt_id}/pictures",
            headers=auth_headers_new,
            json={
                "pictures": [
                    {
                        "source": "https://cdn.example.com/1.jpg",
                        "metadata": {"room": "hall"},
                    }
                ]
            },
        )

    assert resp.status_code == 201
    assert resp.json()["pictures"][0]["metadata"]["format"] == "jpg"
    assert resp.json()["pictures"][0]["metadata"]["size_bytes"] == 777
    picture_url = resp.json()["pictures"][0]["url"]
    apartment_resp = client.get(
        f"/apartment/{apt_id}",
        headers=auth_headers_new)
    picture_id = next(
        p["id_"] for p in apartment_resp.json()["pictures"]
        if p["url"] == picture_url
    )

    resp = client.delete(
        f"/apartment/{apt_id}/pictures/{picture_id}",
        headers=auth_headers_new,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    apartment_resp = client.get(
        f"/apartment/{apt_id}",
        headers=auth_headers_new)
    assert apartment_resp.status_code == 200
    assert apartment_resp.json()["pictures"] == []


def test_delete_apartment_soft_deletes_all_pictures(
    client, auth_headers_new, seeded_owner
):
    """Deleting an apartment should mark all related pictures as deleted."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

    apt_data = {
        "title": "Apartment cascade delete",
        "location": "L",
        "district": "D",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"
    }
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    with patch(
        "src.leorent_backend.services.backblaze_service."
        "backblaze_service.upload_photo_from_source_details",
        new_callable=AsyncMock,
    ) as mock_upload:
        mock_upload.side_effect = [
            {
                "url": "https://b2.example/gallery/one.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 111,
            },
            {
                "url": "https://b2.example/gallery/two.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 222,
            },
        ]
        resp = client.post(
            f"/apartment/{apt_id}/pictures",
            headers=auth_headers_new,
            json={
                "pictures": [
                    {"source": "https://cdn.example.com/1.jpg"},
                    {"source": "https://cdn.example.com/2.jpg"},
                ]
            },
        )

    assert resp.status_code == 201
    assert len(resp.json()["pictures"]) == 2

    resp = client.delete(f"/apartment/{apt_id}", headers=auth_headers_new)
    assert resp.status_code == 204

    resp = client.get(f"/apartment/{apt_id}", headers=auth_headers_new)
    assert resp.status_code == 404


def test_owner_can_soft_delete_all_pictures_without_deleting_apartment(
    client, auth_headers_new, seeded_owner
):
    """Owner can soft-delete all apartment pictures while keeping apartment."""
    app.dependency_overrides[get_current_user] = lambda: seeded_owner
    app.dependency_overrides[get_optional_user] = lambda: seeded_owner

    apt_data = {
        "title": "Apartment bulk picture delete",
        "location": "L",
        "district": "D",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"
    }
    resp = client.post("/apartment/", json=apt_data, headers=auth_headers_new)
    assert resp.status_code == 201
    apt_id = resp.json()["id_"]

    with patch(
        "src.leorent_backend.services.backblaze_service."
        "backblaze_service.upload_photo_from_source_details",
        new_callable=AsyncMock,
    ) as mock_upload:
        mock_upload.side_effect = [
            {
                "url": "https://b2.example/gallery/delete-all-1.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 111,
            },
            {
                "url": "https://b2.example/gallery/delete-all-2.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 222,
            },
        ]
        resp = client.post(
            f"/apartment/{apt_id}/pictures",
            headers=auth_headers_new,
            json={
                "pictures": [
                    {"source": "https://cdn.example.com/1.jpg"},
                    {"source": "https://cdn.example.com/2.jpg"},
                ]
            },
        )

    assert resp.status_code == 201
    assert len(resp.json()["pictures"]) == 2

    resp = client.delete(
        f"/apartment/{apt_id}/pictures",
        headers=auth_headers_new,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    apartment_resp = client.get(
        f"/apartment/{apt_id}",
        headers=auth_headers_new)
    assert apartment_resp.status_code == 200
    assert apartment_resp.json()["pictures"] == []


def test_like_apartment(client, auth_headers_new, seeded_owner, seeded_user):
    """Test POST /apartment/{apartment_id}/like - toggle like functionality."""

    # Create an apartment as owner (using seeded_owner, not seeded_user)
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apt_data = {
        "title": "Apartment to Like",
        "location": "L",
        "district": "D",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"}
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


def test_get_liked_apartments(
        client,
        auth_headers_new,
        seeded_owner,
        seeded_user):
    """Test GET /apartment/liked/ - get liked apartments."""
    # Create apartments as owner
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    apt1_data = {
        "title": "Apartment 1",
        "location": "L1",
        "district": "D1",
        "cost": 100,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 10.0,
        "floor": 1,
        "floor_in_house": 1,
        "type_": "brick",
        "renovation_type": "none"}
    apt2_data = {
        "title": "Apartment 2",
        "location": "L2",
        "district": "D2",
        "cost": 200,
        "rent_type": "DEFAULT",
        "rooms": 2,
        "square": 20.0,
        "floor": 2,
        "floor_in_house": 2,
        "type_": "panel",
        "renovation_type": "cosmetic"}

    apt1_id = client.post(
        "/apartment/",
        json=apt1_data,
        headers=auth_headers_new).json()["id_"]
    apt2_id = client.post(
        "/apartment/",
        json=apt2_data,
        headers=auth_headers_new).json()["id_"]

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


def test_like_and_get_liked_workflow(
        client,
        auth_headers_new,
        seeded_owner,
        seeded_user):
    """Test complete workflow: create apartments, toggle like, get liked list."""
    # Switch to owner to create apartments
    app.dependency_overrides[get_current_user] = lambda: seeded_owner

    # Create 2 apartments
    apt1_data = {
        "title": "Cozy Apartment",
        "location": "Center",
        "district": "Downtown",
        "cost": 150,
        "rent_type": "DEFAULT",
        "rooms": 1,
        "square": 25.0,
        "floor": 3,
        "floor_in_house": 5,
        "type_": "brick",
        "renovation_type": "euro"}
    apt2_data = {
        "title": "Luxury Apartment",
        "location": "Premium",
        "district": "Uptown",
        "cost": 500,
        "rent_type": "DAILY",
        "rooms": 3,
        "square": 80.0,
        "floor": 10,
        "floor_in_house": 15,
        "type_": "monolith",
        "renovation_type": "euro"}

    apt1_id = client.post(
        "/apartment/",
        json=apt1_data,
        headers=auth_headers_new).json()["id_"]
    apt2_id = client.post(
        "/apartment/",
        json=apt2_data,
        headers=auth_headers_new).json()["id_"]

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
