import os

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_question_returns_400():
    response = client.post("/chat", json={"question": ""})
    assert response.status_code == 400
    assert "Please enter a question" in response.json()["detail"]


def test_missing_question_returns_422():
    response = client.post("/chat", json={})
    assert response.status_code == 422


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)
def test_chat_streams_response():
    with client.stream("POST", "/chat/stream", json={"question": "What is Shabbat?"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        chunks = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                chunks.append(line[6:])
        assert len(chunks) > 1, "Should receive multiple chunks"
        full_answer = "".join(chunks)
        assert len(full_answer) > 50
