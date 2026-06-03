async def test_full_auth_flow(client):
    # register
    resp = await client.post(
        "/auth/register",
        json={"email": "ivanov@email.com", "password": "pass1234"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "ivanov@email.com"
    assert "password_hash" not in resp.json()

    # login (form-data, OAuth2PasswordRequestForm)
    resp = await client.post(
        "/auth/login",
        data={"username": "ivanov@email.com", "password": "pass1234"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # /auth/me с валидным токеном
    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "ivanov@email.com"


async def test_duplicate_registration_returns_409(client):
    payload = {"email": "petrov@email.com", "password": "pass1234"}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    assert (await client.post("/auth/register", json=payload)).status_code == 409


async def test_login_with_wrong_password_returns_401(client):
    await client.post(
        "/auth/register",
        json={"email": "sidorov@email.com", "password": "correct-pass"},
    )
    resp = await client.post(
        "/auth/login",
        data={"username": "sidorov@email.com", "password": "wrong-pass"},
    )
    assert resp.status_code == 401


async def test_me_without_token_returns_401(client):
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_with_invalid_token_returns_401(client):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
