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
| Frontend | React + Vite + shadcn/ui |
| Backend | FastAPI (Python) |
| Database | SQLite |
| Auth | JWT + MFA (email code) |
| RAG | LangChain + Weaviate + Cohere Rerank |
| Embeddings | Gemini Embedding 001 |
| LLM | Claude Sonnet |
| Data | Sefaria HuggingFace datasets (3.5M texts) |

## Quick Start

```bash
# Clone
git clone https://github.com/davalimi/torah-study-ai.git
cd torah-study-ai

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run everything
docker compose up
```

Open http://localhost:5173

## Project Structure

```
torah-study-ai/
  src/
    api/          # FastAPI backend
    rag/          # LangChain RAG pipeline
    frontend/     # React + Vite + shadcn/ui
  scripts/        # Download Sefaria, indexing, evaluation
  tests/
  data/           # Local data (gitignored)
  docs/           # Design docs
```

## Documentation

Full project documentation on [skillia.dev/projects/torah-study-ai](https://skillia.dev/projects/torah-study-ai)

## License

MIT
