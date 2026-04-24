from pydantic import BaseModel, field_validator
from src.leorent_backend.models import RentType
from typing import Optional, Any, Dict
from src.leorent_backend.schemas.apartment import ALLOWED_FIELDS, ALLOWED_RENT_TYPES, ALLOWED_TYPES


class FilterPrompt(BaseModel):
    prompt: str

    @field_validator("prompt")
    def check_prompt(cls, v: str) -> str:
        if len(v) >= 150:
            raise ValueError("Prompt must be less than 150 characters")
        return v


class FilterApartment(BaseModel):
    # Default values to None to indicate they are not provided
    location: Optional[str] = None
    district: Optional[str] = None
    type_: Optional[str] = None
    renovation_type: Optional[str] = None
    rent_type: Optional[RentType] = None

    min_cost: Optional[int] = None
    max_cost: Optional[int] = None
    min_square: Optional[float] = None
    max_square: Optional[float] = None
    min_rooms: Optional[int] = None
    max_rooms: Optional[int] = None
    min_floor: Optional[int] = None
    max_floor: Optional[int] = None
    min_floor_in_house: Optional[int] = None
    max_floor_in_house: Optional[int] = None

    details: Optional[Dict[str, bool]] = None

    @field_validator("min_cost", "max_cost")
    @classmethod
    def cost_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Cost must be non-negative")
        return v

    @field_validator("min_square", "max_square")
    @classmethod
    def square_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Square must be non-negative")
        return v

    @field_validator("min_rooms", "max_rooms")
    @classmethod
    def rooms_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Rooms must be non-negative")
        return v

    @field_validator("details", mode="before")
    @classmethod
    def filter_unknown_details(cls, v: Any) -> Optional[Dict[str, bool]]:
        if v is None:
            return None
        if not isinstance(v, dict):
            return None

        # Only keep keys that are in your ALLOWED_FIELDS list and have a non-null value
        filtered = {
            str(key): bool(value)
            for key, value in v.items()
            if key in ALLOWED_FIELDS and value is not None
        }
        return filtered if filtered else None

    @field_validator("rent_type")
    @classmethod
    def rent_type_consistency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in ALLOWED_RENT_TYPES:
            return None
        return v

    @field_validator("renovation_type")
    @classmethod
    def renovation_type_consistency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in ALLOWED_TYPES:
            return None
        return v
