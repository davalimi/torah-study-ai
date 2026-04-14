from collections.abc import Generator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os

from src.api.torah import ask_torah, stream_torah
from src.api.db import init_db, get_connection
from src.api.auth import hash_password, verify_password, create_token, get_current_user_id
from src.rag.pipeline import get_weaviate_client, RAGPipeline

app = FastAPI(title="Torah Study AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single RAG pipeline object (initialized on startup)
rag_pipeline: RAGPipeline | None = None


@app.on_event("startup")
def startup() -> None:
    global rag_pipeline
    init_db()

    try:
        wv_client = get_weaviate_client()
        rag_pipeline = RAGPipeline(wv_client)
    except Exception:
        pass  # RAG not available, fallback to direct LLM


# --- Models ---

class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


class AuthRequest(BaseModel):
    email: str
    password: str


class MessageRequest(BaseModel):
    role: str
    content: str


# --- Health ---

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Auth ---

@app.post("/auth/register")
def register(req: AuthRequest) -> dict[str, str]:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (req.email, hash_password(req.password)),
        )
        conn.commit()
        user = conn.execute("SELECT id FROM users WHERE email = ?", (req.email,)).fetchone()
        return {"token": create_token(user["id"])}
    except Exception:
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        conn.close()


@app.post("/auth/login")
def login(req: AuthRequest) -> dict[str, str]:
    conn = get_connection()
    user = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (req.email,)).fetchone()
    conn.close()

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": create_token(user["id"])}


# --- Sessions ---

@app.get("/sessions")
def list_sessions(request: Request) -> list[dict]:
    user_id = get_current_user_id(request)
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/sessions")
def create_session(request: Request) -> dict:
    user_id = get_current_user_id(request)
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO sessions (user_id) VALUES (?)",
        (user_id,),
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return {"id": session_id}


@app.get("/sessions/{session_id}")
def get_session(session_id: int, request: Request) -> dict:
    user_id = get_current_user_id(request)
    conn = get_connection()

    session = conn.execute(
        "SELECT id, title, created_at FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    messages = conn.execute(
        "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    conn.close()

    return {
        "id": session["id"],
        "title": session["title"],
        "messages": [dict(m) for m in messages],
    }


@app.post("/sessions/{session_id}/messages")
def add_message(session_id: int, msg: MessageRequest, request: Request) -> dict[str, str]:
    user_id = get_current_user_id(request)
    conn = get_connection()

    session = conn.execute(
        "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, msg.role, msg.content),
    )

    # Update session title from first user message
    if msg.role == "user":
        first = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()
        if first["cnt"] == 1:
            title = msg.content[:80]
            conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))

    conn.execute("UPDATE sessions SET updated_at = datetime('now') WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# --- Chat ---

@app.post("/chat", response_model=ChatResponse)
def chat(request_body: ChatRequest) -> ChatResponse:
    if not request_body.question.strip():
        raise HTTPException(status_code=400, detail="Please enter a question")

    if rag_pipeline:
        answer = rag_pipeline.ask(request_body.question)
        return ChatResponse(answer=answer)

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not set")

    try:
        answer = ask_torah(request_body.question, api_key=api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ChatResponse(answer=answer)


def _sse_generator(question: str) -> Generator[str, None, None]:
    """SSE generator. Encodes chunks as JSON to preserve newlines."""
    import json

    # Use LangChain RAG pipeline if available, otherwise fallback to direct LLM
    if rag_pipeline:
        stream = rag_pipeline.stream(question)
    else:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        stream = stream_torah(question, api_key=api_key)

    for chunk in stream:
        payload = json.dumps({"text": chunk})
        yield f"data: {payload}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/chat/stream")
def chat_stream(request_body: ChatRequest) -> StreamingResponse:
    if not rag_pipeline and not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not set")

    if not request_body.question.strip():
        raise HTTPException(status_code=400, detail="Please enter a question")

    return StreamingResponse(
        _sse_generator(request_body.question),
        media_type="text/event-stream",
    )
