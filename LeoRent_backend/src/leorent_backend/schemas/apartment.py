from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from uuid import UUID


# ==== ALLOWED CONSTANTS

ALLOWED_RENT_TYPES = ['DEFAULT', 'DAILY']
ALLOWED_TYPES = [
    "panel",
    "brick",
    "monolith"
]
ALLOWED_RENOVATION_TYPES = [
    "euro",
    "cosmetic",
    "none"
]
ALLOWED_FIELDS = [
    "wifi",
    "elevator",
    "washing_machine",
    "parking",
    "furniture",
    "animals",
    "balcony",
    "conditioner"
]


class ApartmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    location: str
    district: str
    cost: int
    rent_type: str
    rooms: int
    square: float
    floor: int
    floor_in_house: int
    details: Optional[Dict[str, Any]] = None
    type_: str
    renovation_type: str

    @field_validator('cost')
    def cost_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Cost must be positive')
        return v

    @field_validator('rooms')
    def rooms_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Rooms must be positive')
        return v

    @field_validator('square')
    def square_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Square must be positive')
        return v

    @field_validator('floor')
    def floor_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Floor must be positive')
        return v

    @field_validator('floor_in_house')
    def floor_in_house_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Floor in house must be positive')
        return v

    @field_validator('details')
    def details_consistency(cls, v):
        if v is None:
            return v
        for key in v.keys():
            if key not in ALLOWED_FIELDS:
                raise ValueError(f'Field {key} is not allowed')
        return v

    @field_validator('rent_type')
    def rent_type_consistency(cls, v):
        if v not in ALLOWED_RENT_TYPES:
            raise ValueError(f'Rent type {v} is not allowed')
        return v

    @field_validator('type_')
    def type_consistency(cls, v):
        if v not in ALLOWED_TYPES:
            raise ValueError(f'Type {v} is not allowed')
        return v

    @field_validator('renovation_type')
    def renovation_type_consistency(cls, v):
        if v not in ALLOWED_RENOVATION_TYPES:
            raise ValueError(f'Renovation type {v} is not allowed')
        return v


class ApartmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    district: Optional[str] = None
    cost: Optional[int] = None
    rent_type: Optional[str] = None
    rooms: Optional[int] = None
    square: Optional[float] = None
    floor: Optional[int] = None
    floor_in_house: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    type_: Optional[str] = None
    renovation_type: Optional[str] = None

    # TODO: Add validation for update fields


# ========= Response Schemas =========


# ======== FULL Schema ========

class ApartmentFullInfoResponse(BaseModel):
    id_: UUID
    title: str
    description: Optional[str] = None
    location: str
    district: str
    cost: int
    rent_type: str
    rooms: int
    square: float
    floor: int
    floor_in_house: int
    details: Optional[Dict[str, Any]] = None
    type_: str
    renovation_type: str
    owner_type: str
    owner_info: Dict[str, Any]


class ApartmentResponse(BaseModel):
    id_: UUID
    title: str
    description: Optional[str] = None
    location: str
    district: str
    cost: int
    rent_type: str
    is_deleted: bool = False
    rooms: int
    square: float
    floor: int
    floor_in_house: int
    details: Optional[Dict[str, Any]] = None
    type_: str
    renovation_type: str
    owner: UUID


class ApartmentListResponse(BaseModel):
    apartments: list[ApartmentResponse]


class ApartmentPreviewResponse(BaseModel):
    id_: UUID
    title: str
    cost: int
    rent_type: str
    rooms: int
    square: float
    floor: int
    floor_in_house: int
    type_: str
    renovation_type: str
    location: str
    district: str
    owner_type: str
    is_liked_by_current_user: bool = False


class ApartmentPreviewListResponse(BaseModel):
    apartments: list[ApartmentPreviewResponse]


class ApartmentLikeResponse(BaseModel):
    message: str
    status: str
