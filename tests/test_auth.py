import os
import pytest
from fastapi.testclient import TestClient

# Use a test database
os.environ["DB_PATH"] = "data/test.db"

from src.api.main import app
from src.api.db import init_db, get_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    init_db()
    yield
    conn = get_connection()
    conn.executescript("DELETE FROM messages; DELETE FROM sessions; DELETE FROM users;")
    conn.close()


def test_register():
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secure123",
    })
    assert response.status_code == 200
    assert "token" in response.json()


def test_register_duplicate_email():
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secure123",
    })
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "other456",
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login():
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secure123",
    })
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "secure123",
    })
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_wrong_password():
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secure123",
    })
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrong",
    })
    assert response.status_code == 401


def test_sessions_requires_auth():
    response = client.get("/sessions")
    assert response.status_code == 401


def test_create_session_and_list():
    # Register and get token
    reg = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secure123",
    })
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a session
    response = client.post("/sessions", headers=headers)
    assert response.status_code == 200
    session_id = response.json()["id"]

    # List sessions
    response = client.get("/sessions", headers=headers)
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id


def test_save_and_retrieve_messages():
    # Register and get token
    reg = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secure123",
    })
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    session = client.post("/sessions", headers=headers)
    session_id = session.json()["id"]

    # Save messages
    client.post(f"/sessions/{session_id}/messages", headers=headers, json={
        "role": "user",
        "content": "What is Shabbat?",
    })
    client.post(f"/sessions/{session_id}/messages", headers=headers, json={
        "role": "assistant",
        "content": "Shabbat is the weekly day of rest...",
    })

    # Retrieve messages
    response = client.get(f"/sessions/{session_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
