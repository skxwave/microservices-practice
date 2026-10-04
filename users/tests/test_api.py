async def test_health(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_get_user_not_found(client, db):
    db.scalar.return_value = None

    response = await client.get("/users/1")

    assert response.status_code == 404
