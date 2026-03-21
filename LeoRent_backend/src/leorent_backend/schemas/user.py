from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class CreateUser(BaseModel):
    email: str
    username: str
    phone: str
    password: str
    user_type: str
    # TODO: Add validation and default values for user_type


class LoginUser(BaseModel):
    email: str
    password: str
    # TODO: Add validation and default values for user_type
