from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src import get_db
from src.config import settings
from src.auth import (
    AuthService,
    get_access_payload,
    get_auth_service,
    get_current_user,
    hash_password,
)
from src.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    TokenPayload,
    UserCreate,
    UserRegister,
    UserResponse,
)
from src.models import User
from src.events import send_user_created_event, start_producer, stop_producer
from src.redis_client import start_redis, stop_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    await start_redis()
    yield
    await stop_redis()
    await stop_producer()


app = FastAPI(
    title="Users service",
    description="Microservice on FastAPI to manage users",
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenPair)
async def login(
    credentials: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    return await auth.login(credentials.username, credentials.password)


@app.post("/auth/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    return await auth.refresh(body.refresh_token)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    access: Annotated[TokenPayload, Depends(get_access_payload)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth.logout(access, body.refresh_token)


@app.get("/users/me", response_model=UserResponse)
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    return UserResponse.model_validate(user, from_attributes=True)


@app.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[Depends(get_current_user)],
)
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    users = await db.scalars(select(User))
    result = []

    for user in users:
        result.append(
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
            )
        )

    return result


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await db.scalar(
        select(User).where(User.id == user_id),
    )

    if not user:
        raise HTTPException(
            detail="user not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
    )


@app.post("/users", response_model=UserResponse)
async def create_user(
    user: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    old_user = await db.scalar(
        select(User).where(
            or_(User.username == user.username, User.email == user.email)
        )
    )

    if old_user:
        raise HTTPException(
            detail="user already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    new_user = User(
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hash=await hash_password(user.password),
    )

    db.add(new_user)
    await db.commit()

    await send_user_created_event(
        {
            "username": new_user.username,
            "email": new_user.email,
        }
    )

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
    )


@app.post("/debug/user_create_event")
async def debug_user_create_event(
    user: UserCreate
):
    await send_user_created_event({
        "username": user.username,
        "email": user.email,
    })
    return {"details": "event sent"}
