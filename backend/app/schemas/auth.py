"""
Pydantic v2 Schemas for Authentication & User Management.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, description="Optional phone number e.g. +919876543210")


class LoginRequest(BaseModel):
    email: str
    password: str


class SendOTPRequest(BaseModel):
    phone_or_email: str = Field(..., description="Mobile number (e.g. +919876543210 or 9876543210) or Email")


class SendOTPResponse(BaseModel):
    success: bool
    message: str
    phone_or_email: str
    dev_otp_code: Optional[str] = None  # Returned in dev / test mode for automated ease


class VerifyOTPRequest(BaseModel):
    phone_or_email: str
    otp_code: str = Field(..., min_length=4, max_length=10)
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
