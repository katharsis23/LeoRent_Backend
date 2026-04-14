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
    # Default values to avoid empty request
    renovation_type: Optional[str]
    cost: Optional[int] = 0
    square: Optional[float] = 0.0
    rooms: Optional[int] = 0
    rent_type: Optional[RentType] = 'DEFAULT'
    floor: Optional[int] = 0
    floor_in_house: Optional[int] = 0
    details: Optional[Dict[Any, bool]]

    @field_validator("cost")
    def cost_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Cost must be non-negative")
        return v

    @field_validator("square")
    def square_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Square must be non-negative")
        return v

    @field_validator("rooms")
    def rooms_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Rooms must be non-negative")
        return v

    @field_validator("floor")
    def floor_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Floor must be non-negative")
        return v

    @field_validator("floor_in_house")
    def floor_in_house_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Floor in house must be non-negative")
        return v

    @field_validator("details", mode="before")
    def filter_unknown_details(cls, v: Any) -> Dict[str, bool]:
        if not isinstance(v, dict):
            return {}

        # Only keep keys that are in your ALLOWED_FIELDS list
        return {
            str(key): bool(value)
            for key, value in v.items()
            if key in ALLOWED_FIELDS
        }

    @field_validator("rent_type")
    def rent_type_consistency(cls, v: str) -> str:
        if v not in ALLOWED_RENT_TYPES:
            return 'DEFAULT'
        return v

    @field_validator("renovation_type")
    def renovation_type_consistency(cls, v: str) -> str:
        if v not in ALLOWED_TYPES:
            return 'none'
        return v
