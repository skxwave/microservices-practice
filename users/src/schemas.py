from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class BaseUser(BaseModel):
    username: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(BaseUser):
    pass


class UserRegister(BaseUser):
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseUser):
    id: int


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    jti: str
    type: Literal["access", "refresh"]
    iat: int
    exp: int
