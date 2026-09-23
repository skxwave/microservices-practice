from pydantic import BaseModel, EmailStr


class BaseUser(BaseModel):
    username: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(BaseUser):
    pass


class UserResponse(BaseUser):
    id: int
