from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.leorent_backend.schemas.filter import FilterApartment


GEMINI_GENERATE_JSON_PATH = (
    "src.leorent_backend.routers.filter."
    "FilterRouter.gemini_client.generate_json"
)


def test_filter_apartment_normalizes_defaults_and_details():
    apartment_filter = FilterApartment(
        renovation_type="invalid-value",
        cost=12000,
        square=42.5,
        rooms=2,
        rent_type="invalid-rent-type",
        floor=3,
        floor_in_house=9,
        details={"wifi": 1, "animals": False, "unknown": True},
    )

    rent_type_value = getattr(
        apartment_filter.rent_type,
        "value",
        apartment_filter.rent_type,
    )

    assert rent_type_value == "DEFAULT"
    assert apartment_filter.renovation_type == "none"
    assert apartment_filter.details == {"wifi": True, "animals": False}


def test_filter_apartment_keeps_valid_renovation_type():
    apartment_filter = FilterApartment(
        renovation_type="euro",
        cost=12000,
    )

    assert apartment_filter.renovation_type == "euro"


def test_filter_apartment_rejects_negative_values():
    with pytest.raises(ValueError, match="Cost must be non-negative"):
        FilterApartment(renovation_type="euro", cost=-1)


def test_ai_search_returns_preview_list(client):
    apartment = SimpleNamespace(
        id_=uuid4(),
        title="Filter test apartment",
        cost=19000,
        rent_type="DEFAULT",
        rooms=2,
        square=54.0,
        floor=6,
        floor_in_house=12,
        type_="brick",
        renovation_type="euro",
        location="Kyiv",
        district="Pechersk",
        owner="OWNER",
        picture="https://example.com/apartment.jpg",
    )

    with patch(
        GEMINI_GENERATE_JSON_PATH,
        new=AsyncMock(
            return_value={
                "renovation_type": "euro",
                "cost": 20000,
                "square": 50,
                "rooms": 2,
                "rent_type": "DEFAULT",
                "floor": 4,
                "floor_in_house": 10,
                "details": {"wifi": True},
            }
        ),
    ), patch(
        "src.leorent_backend.routers.filter.get_apartments_by_gemini_filter",
        new=AsyncMock(return_value=[apartment]),
    ) as mock_get_apartments:
        response = client.get(
            "/filter/ai-search",
            params={
                "prompt": "2-room apartment in Kyiv",
                "page": 2,
                "size": 5,
            },
        )

    assert response.status_code == 200
    assert response.json()["apartments"][0]["title"] == "Filter test apartment"
    assert response.json()["apartments"][0]["owner_type"] == "OWNER"
    mock_get_apartments.assert_awaited_once()
    await_args = mock_get_apartments.await_args.kwargs
    assert await_args["current_page"] == 2
    assert await_args["page_size"] == 5
    assert await_args["filter_query"].details == {"wifi": True}
    assert await_args["filter_query"].renovation_type == "euro"


def test_ai_search_returns_422_for_invalid_ai_output(client):
    with patch(
        GEMINI_GENERATE_JSON_PATH,
        new=AsyncMock(return_value={"cost": -10}),
    ), patch(
        "src.leorent_backend.routers.filter.get_apartments_by_gemini_filter",
        new=AsyncMock(),
    ) as mock_get_apartments:
        response = client.get(
            "/filter/ai-search",
            params={"prompt": "cheap apartment"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "AI output didn't match internal filter schema."
    }
    mock_get_apartments.assert_not_called()
