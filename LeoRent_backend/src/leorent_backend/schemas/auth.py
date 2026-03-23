from pydantic import BaseModel, Field
from typing import Optional


class FirebaseAuthRequest(BaseModel):
    id_token: str = Field(..., description="Firebase ID token")


class FirebaseUserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    phone_number: Optional[str] = Field(None, description="Phone number")
    user_type: str = Field(..., description="User type")
    firebase_uid: Optional[str] = Field(None, description="Firebase UID")
    is_verified: bool = Field(..., description="Email verification status")
