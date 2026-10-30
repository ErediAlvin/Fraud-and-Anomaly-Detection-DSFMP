"""
DSFMP Fraud Detection — Authentication Schemas

Pydantic models for auth requests and responses.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str = Field(..., serialization_alias="firstName")
    last_name: str = Field(..., serialization_alias="lastName")
    role: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = Field(None, serialization_alias="avatarUrl")
    two_fa_enabled: bool = Field(..., serialization_alias="twoFaEnabled")

    class Config:
        from_attributes = True
        populate_by_name = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = None


class LoginResponse(BaseModel):
    requires_2fa: bool = Field(..., serialization_alias="requires2Fa")
    temp_token: Optional[str] = Field(None, serialization_alias="tempToken")
    access_token: Optional[str] = Field(None, serialization_alias="accessToken")
    refresh_token: Optional[str] = Field(None, serialization_alias="refreshToken")
    user: Optional[UserResponse] = None

    class Config:
        populate_by_name = True


class Verify2FARequest(BaseModel):
    temp_token: str
    otp_code: str = Field(..., min_length=6, max_length=6)

    class Config:
        populate_by_name = True


class RefreshRequest(BaseModel):
    refresh_token: str

    class Config:
        populate_by_name = True


class TokenResponse(BaseModel):
    access_token: str = Field(..., serialization_alias="accessToken")
    refresh_token: str = Field(..., serialization_alias="refreshToken")
    token_type: str = Field("bearer", serialization_alias="tokenType")

    class Config:
        populate_by_name = True

