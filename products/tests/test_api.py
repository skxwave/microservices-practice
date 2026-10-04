from main import app
from src.services.user_service import user_service


async def test_health(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_product_unknown_user(client, db):
    class NoUsers:
        async def get_user(self, user_id):
            return None

    app.dependency_overrides[user_service] = lambda: NoUsers()

    response = await client.post(
        "/products",
        json={"user_id": 1, "title": "t", "description": "d", "price": 1},
    )

    assert response.status_code == 404
