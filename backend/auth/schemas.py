from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    REVIEWER = "REVIEWER"
    READ_ONLY = "READ_ONLY"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: UserRole


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    username_or_email: str = Field(description="Username or registered email address")
    password: str = Field(description="Plaintext password")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.READ_ONLY
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None
