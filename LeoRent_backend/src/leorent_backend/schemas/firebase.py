from pydantic import BaseModel, Field
from typing import Optional


class FirebaseUserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    user_type: str = Field(..., description="User type")
    is_verified: bool = Field(..., description="Email verification status")
    firebase_uid: Optional[str] = Field(None, description="Firebase UID")


class FirebaseAuthResponse(BaseModel):
    message: str = Field(..., description="Response message")
    user: FirebaseUserResponse = Field(..., description="User data")
