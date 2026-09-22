import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_db
from core.schemas import UserCreate, UserResponse
from core.models import User

load_dotenv()

app = FastAPI(
    title="Users service",
    description="Microservice on FastAPI to manage users",
    debug=os.getenv("DEBUG", True),
)


@app.get("/users", response_model=list[UserResponse])
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    users = await db.scalars(select(User))
    result = []

    for user in users:
        result.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        ))
    
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
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    old_user = await db.scalar(
        select(User).where(or_(User.username == user.username, User.email == user.email))
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
    )

    db.add(new_user)
    await db.commit()

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
    )
