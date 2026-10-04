import httpx

from src.config import settings

from .user_dtos import UserDTO


class UserService:
    def __init__(self):
        self.url = settings.user_service_url

    async def get_user(self, user_id: int) -> UserDTO:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url + f"/users/{user_id}", timeout=30)
            if response.status_code == 404:
                return None
            return UserDTO(**response.json())


async def user_service():
    return UserService()
