# Torah Study AI

Your AI study partner for Torah. Real sources. Every answer.

An AI chavruta that helps you explore Torah, Talmud, and Jewish texts with verifiable sources from [Sefaria](https://sefaria.org).

## Features

- **Chat with sources** - Ask a question, get an answer with clickable Sefaria links
- **Conversation history** - Sidebar with past chats, resume any conversation
- **Multi-language** - French interface, Hebrew quotes, answer in your language
- **Parashah of the week** - Weekly Torah portion with key insights

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js + shadcn/ui |
| Backend | FastAPI (Python) |
| Database | SQLite |
| Auth | JWT + bcrypt |
| RAG | LangChain + Weaviate + Cohere Rerank |
| Embeddings | Gemini Embedding 001 |
| LLM | Gemini 2.5 Flash |
| Data | Sefaria HuggingFace datasets (3.5M texts) |

## Quick Start

```bash
# Clone
git clone https://github.com/davalimi/torah-study-ai.git
cd torah-study-ai

# Set up environment
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY

# Install
make install
make install-frontend

# Run (2 terminals)
make api        # Terminal 1: API on localhost:8000
make frontend   # Terminal 2: Frontend on localhost:3000
```

Open http://localhost:3000

## Project Structure

```
torah-study-ai/
  src/
    api/          # FastAPI backend (auth, chat, sessions)
    frontend/     # Next.js + shadcn/ui
    rag/          # LangChain RAG pipeline (Block 3)
  scripts/        # Download Sefaria, indexing, evaluation
  tests/          # pytest (18 tests)
  data/           # SQLite DB + local data (gitignored)
```

## Documentation

Full project documentation on [skillia.dev/projects/torah-study-ai](https://skillia.dev/projects/torah-study-ai)

## License

MIT
