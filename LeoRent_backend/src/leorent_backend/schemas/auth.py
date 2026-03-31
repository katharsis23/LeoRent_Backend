from pydantic import BaseModel, Field, field_validator
from typing import Optional
from src.leorent_backend.models import UserType


class FirebaseAuthRequest(BaseModel):
    id_token: str = Field(..., description="Firebase ID token")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    phone: str = Field(..., description="User's phone number")
    user_type: UserType = Field(UserType.DEFAULT, description="User type")

    @field_validator("user_type", mode="before")
    @classmethod
    def validate_user_type(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        return v


class FirebaseUserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    phone_number: Optional[str] = Field(None, description="Phone number")
    user_type: str = Field(..., description="User type")
    firebase_uid: Optional[str] = Field(None, description="Firebase UID")
    is_verified: bool = Field(..., description="Email verification status")
