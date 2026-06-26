import datetime
import secrets

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select

from app.db.models import async_session, User
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.api.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, RefreshRequest,
)
from app.core.dependencies import require_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest):
    async with async_session() as session:
        existing = await session.execute(
            select(User).where(
                (User.username == body.username) | (User.email == body.email)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username or email already exists")

        user = User(
            username=body.username,
            email=body.email,
            hashed_password=hash_password(body.password),
            role=body.role or "analyst",
            api_key=secrets.token_hex(24),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return {"message": "User created", "username": user.username, "api_key": user.api_key}


@router.post("/login")
async def login(body: LoginRequest):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == body.username)
        )
        user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.disabled:
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token = create_access_token({"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.username})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    username = payload.get("sub")
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

    if not user or user.disabled:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    access_token = create_access_token({"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.username})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/me")
async def me(user=Depends(require_user)):
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "api_key": user.api_key,
    }
