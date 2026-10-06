import time
from unittest.mock import MagicMock

import jwt

from src.auth import _hasher
from src.config import settings

PASSWORD = "correct-horse"


def make_user(user_id=1):
    user = MagicMock()
    user.id = user_id
    user.username = "john"
    user.email = "john@example.com"
    user.first_name = "John"
    user.last_name = "Doe"
    user.password_hash = _hasher.hash(PASSWORD)
    return user


async def login(client, db, redis):
    db.scalar.return_value = make_user()
    response = await client.post(
        "/auth/login", json={"username": "john", "password": PASSWORD}
    )
    assert response.status_code == 200
    return response.json()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


async def test_login_success(client, db, redis):
    tokens = await login(client, db, redis)

    claims = jwt.decode(tokens["access_token"], settings.jwt_secret, [settings.jwt_algorithm])
    assert claims["sub"] == "1"
    assert claims["type"] == "access"


async def test_login_wrong_password(client, db, redis):
    db.scalar.return_value = make_user()

    response = await client.post(
        "/auth/login", json={"username": "john", "password": "wrong-password"}
    )

    assert response.status_code == 401


async def test_login_unknown_user(client, db, redis):
    db.scalar.return_value = None

    response = await client.post(
        "/auth/login", json={"username": "ghost", "password": PASSWORD}
    )

    assert response.status_code == 401


async def test_locked_endpoint_requires_token(client, db, redis):
    response = await client.get("/users/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_with_valid_token(client, db, redis):
    tokens = await login(client, db, redis)

    response = await client.get("/users/me", headers=bearer(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json()["username"] == "john"


async def test_refresh_token_rejected_as_access(client, db, redis):
    tokens = await login(client, db, redis)

    response = await client.get("/users/me", headers=bearer(tokens["refresh_token"]))

    assert response.status_code == 401


async def test_expired_token_rejected(client, db, redis):
    now = int(time.time())
    token = jwt.encode(
        {"sub": "1", "jti": "x", "type": "access", "iat": now - 100, "exp": now - 10},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/users/me", headers=bearer(token))

    assert response.status_code == 401


async def test_token_signed_with_other_secret_rejected(client, db, redis):
    now = int(time.time())
    token = jwt.encode(
        {"sub": "1", "jti": "x", "type": "access", "iat": now, "exp": now + 100},
        "another-secret-another-secret-123",
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/users/me", headers=bearer(token))

    assert response.status_code == 401


async def test_unsigned_token_rejected(client, db, redis):
    now = int(time.time())
    token = jwt.encode(
        {"sub": "1", "jti": "x", "type": "access", "iat": now, "exp": now + 100},
        None,
        algorithm="none",
    )

    response = await client.get("/users/me", headers=bearer(token))

    assert response.status_code == 401


async def test_refresh_rotates_and_blacklists_old_token(client, db, redis):
    tokens = await login(client, db, redis)

    first = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    replay = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert first.status_code == 200
    assert first.json()["refresh_token"] != tokens["refresh_token"]
    assert replay.status_code == 401


async def test_access_token_rejected_as_refresh(client, db, redis):
    tokens = await login(client, db, redis)

    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401


async def test_logout_blacklists_both_tokens(client, db, redis):
    tokens = await login(client, db, redis)

    response = await client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=bearer(tokens["access_token"]),
    )
    me = await client.get("/users/me", headers=bearer(tokens["access_token"]))
    refresh = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 204
    assert me.status_code == 401
    assert refresh.status_code == 401


async def test_logout_with_foreign_refresh_token_rejected(client, db, redis):
    mine = await login(client, db, redis)
    db.scalar.return_value = make_user(user_id=2)
    other = await client.post(
        "/auth/login", json={"username": "john", "password": PASSWORD}
    )

    response = await client.post(
        "/auth/logout",
        json={"refresh_token": other.json()["refresh_token"]},
        headers=bearer(mine["access_token"]),
    )

    assert response.status_code == 401


async def test_users_list_requires_token(client, db, redis):
    response = await client.get("/users")

    assert response.status_code == 401
