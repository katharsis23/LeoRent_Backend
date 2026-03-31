from pydantic import BaseModel, Field, field_validator
import re
from src.leorent_backend.models import UserType
from typing import Optional


def email_validation(v: str) -> str:
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
        raise ValueError("Email must be valid")
    return v.lower()


class CreateUser(BaseModel):
    email: str
    username: str = Field(..., min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    phone: str = Field(..., description="Phone number with country code, e.g. +380...")
    password: str = Field(..., min_length=8)
    # TODO: Double check validity of user_type
    user_type: UserType = UserType.DEFAULT

    @field_validator("user_type", mode="before")
    @classmethod
    def validate_user_type_enum(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Basic regex for phone: + and 7-15 digits
        if not re.match(r"^\+\d{7,15}$", v):
            raise ValueError("Phone number must start with + and contain 7-15 digits")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return email_validation(v)


class LoginUser(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return email_validation(v)
