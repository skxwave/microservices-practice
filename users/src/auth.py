import asyncio
import time
import uuid
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src import get_db
from src.config import settings
from src.models import User
from src.redis_client import get_redis
from src.schemas import TokenPair, TokenPayload

_bearer = HTTPBearer(auto_error=False)
_hasher = PasswordHasher()
# Verified against when the user is unknown so login timing doesn't reveal which usernames exist.
_DUMMY_HASH = _hasher.hash("dummy-password")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


async def _verify_password(password_hash: str, password: str) -> bool:
    try:
        return await asyncio.to_thread(_hasher.verify, password_hash, password)
    except VerifyMismatchError:
        return False


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def login(self, username: str, password: str) -> TokenPair:
        user = await self.db.scalar(select(User).where(User.username == username))

        valid = await _verify_password(
            user.password_hash if user else _DUMMY_HASH, password
        )
        if not (user and valid):
            raise _unauthorized("invalid credentials")

        return self._issue_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = await self.decode(refresh_token, "refresh")
        user = await self.get_user(payload.sub)

        # atomic: of two concurrent refreshes with the same token only one wins
        if not await self._revoke(payload):
            raise _unauthorized("token revoked")

        return self._issue_pair(user.id)

    async def logout(self, access: TokenPayload, refresh_token: str) -> None:
        refresh = await self.decode(refresh_token, "refresh")
        if refresh.sub != access.sub:
            raise _unauthorized("invalid token")

        await self._revoke(access)
        await self._revoke(refresh)

    async def decode(self, token: str, expected_type: str) -> TokenPayload:
        try:
            claims = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"require": ["sub", "jti", "iat", "exp"]},
            )
            payload = TokenPayload.model_validate(claims)
        except (jwt.PyJWTError, ValidationError):
            raise _unauthorized("invalid token")

        if payload.type != expected_type:
            raise _unauthorized("invalid token")
        if await self.redis.exists(self._blacklist_key(payload.jti)):
            raise _unauthorized("token revoked")
        return payload

    async def get_user(self, sub: str) -> User:
        user = await self.db.scalar(select(User).where(User.id == int(sub)))
        if not user:
            raise _unauthorized("invalid token")
        return user

    def _issue_pair(self, user_id: int) -> TokenPair:
        return TokenPair(
            access_token=self._encode(
                user_id, "access", settings.access_token_ttl_minutes * 60
            ),
            refresh_token=self._encode(
                user_id, "refresh", settings.refresh_token_ttl_days * 86400
            ),
        )

    def _encode(self, user_id: int, token_type: str, ttl_seconds: int) -> str:
        now = int(time.time())
        payload = TokenPayload(
            sub=str(user_id),
            jti=uuid.uuid4().hex,
            type=token_type,
            iat=now,
            exp=now + ttl_seconds,
        )
        return jwt.encode(
            payload.model_dump(),
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

    async def _revoke(self, payload: TokenPayload) -> bool:
        ttl = payload.exp - int(time.time())
        if ttl <= 0:
            return True
        return bool(
            await self.redis.set(self._blacklist_key(payload.jti), 1, ex=ttl, nx=True)
        )

    @staticmethod
    def _blacklist_key(jti: str) -> str:
        return f"token:blacklist:{jti}"


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthService:
    return AuthService(db, redis)


async def get_access_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPayload:
    if not credentials:
        raise _unauthorized("not authenticated")
    return await auth.decode(credentials.credentials, "access")


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_access_payload)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return await auth.get_user(payload.sub)
