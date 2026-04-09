import pytest
from app.core.auth import hash_password, verify_password, create_jwt, decode_jwt

def test_password_hash_and_verify():
    hashed = hash_password("testpass123")
    assert verify_password("testpass123", hashed)
    assert not verify_password("wrongpass", hashed)

def test_jwt_create_and_decode():
    token = create_jwt(user_id=1, username="admin")
    payload = decode_jwt(token)
    assert payload["sub"] == "1"
    assert payload["username"] == "admin"

def test_jwt_invalid_token():
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        decode_jwt("invalid.token.here")

@pytest.mark.asyncio
async def test_setup_creates_root_user(client):
    resp = await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "root"
    assert data["role"] == "root"

@pytest.mark.asyncio
async def test_setup_only_works_once(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    resp = await client.post("/api/auth/setup", json={"username": "root2", "password": "pass"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    resp = await client.post("/api/auth/login", json={"username": "root", "password": "rootpass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.cookies

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    resp = await client.post("/api/auth/login", json={"username": "root", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_authenticated(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    await client.post("/api/auth/login", json={"username": "root", "password": "rootpass123"})
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "root"

@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
