"""User authentication routes for DevMind AI (Registration, Login, Profile, Logout)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_strict_current_user
from app.api.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.db import crud
from app.db.database import get_db
from app.db.models import UserModel
from app.utils.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account with normalized email and Argon2id hashed credentials.

    Args:
        payload: RegisterRequest containing email, password, and optional full_name.
        db: Active database session.

    Returns:
        UserResponse with safe user profile information (no secrets or hashes).

    Raises:
        HTTPException(409): If an account with the specified email already exists.
        HTTPException(400): If validation fails.
    """
    normalized_email = payload.email.strip().lower()

    # Check for existing account
    existing_user = crud.get_user_by_email(db, email=normalized_email)
    if existing_user:
        logger.warning("Registration rejected: account already exists for '%s'", normalized_email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # Securely hash password with Argon2id
    try:
        pw_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Persist user record
    user = crud.create_user(
        db,
        email=normalized_email,
        password_hash=pw_hash,
        full_name=payload.full_name,
    )
    logger.info("Created new user account: id=%d, email=%s", user.id, user.email)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access token",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email and password, issuing a signed JWT access token.

    Employs generic error responses to eliminate account enumeration vulnerabilities.

    Args:
        payload: LoginRequest containing email and password.
        db: Active database session.

    Returns:
        TokenResponse with JWT access token and public user profile.

    Raises:
        HTTPException(401): On invalid credentials or inactive account.
    """
    normalized_email = payload.email.strip().lower()
    user = crud.get_user_by_email(db, email=normalized_email)

    # Validate password using constant-time Argon2id verification
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        logger.warning("Failed login attempt for email: %s", normalized_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue signed JWT access token
    token = create_access_token(user_id=user.id, email=user.email)
    logger.info("Successful authentication for user id=%d (%s)", user.id, user.email)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get profile of currently authenticated user",
)
def get_current_user_profile(
    current_user: UserModel = Depends(get_strict_current_user),
) -> UserResponse:
    """Return the currently authenticated user's safe profile.

    Requires an active and valid Bearer access token in the Authorization header.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out user (client session cleanup)",
)
def logout(
    current_user: UserModel = Depends(get_strict_current_user),
) -> MessageResponse:
    """Acknowledge client logout and signal client-side session cleanup.

    JWT access tokens are stateless and bounded by expiration (JWT_ACCESS_TOKEN_EXPIRE_MINUTES).
    Clients must discard the access token from storage upon calling this endpoint.
    """
    logger.info("User id=%d initiated client logout", current_user.id)
    return MessageResponse(
        message="Successfully logged out. Please discard your local access token."
    )
