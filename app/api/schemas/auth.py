"""Pydantic schemas for authentication and user account requests and responses."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """Payload for user account registration."""

    email: str = Field(..., description="User's unique email address", min_length=3, max_length=255)
    password: str = Field(..., description="Plaintext password (minimum 8 characters)", min_length=8)
    full_name: Optional[str] = Field(None, description="Optional full name or display name", max_length=255)

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        """Validate email format and normalize to lowercase."""
        cleaned = v.strip().lower()
        # Basic RFC-compliant email regex pattern
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, cleaned):
            raise ValueError("Invalid email format.")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Enforce password security constraints."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Public user profile response (safe, zero secrets)."""

    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Authentication token response issued upon successful login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic status or notification response."""

    message: str
