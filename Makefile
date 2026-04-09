.PHONY: test test-all install install-frontend api frontend clean

# Run unit tests only (no API calls)
test:
	source .venv/bin/activate && python -m pytest tests/ -v -k "not basic_question and not system_prompt and not halakhic"

# Run all tests (needs GOOGLE_API_KEY in .env)
test-all:
	source .venv/bin/activate && set -a && source .env && set +a && python -m pytest tests/ -v

# Install Python dependencies
install:
	python3 -m venv .venv
	source .venv/bin/activate && pip install -r requirements.txt

# Install frontend dependencies
install-frontend:
	cd src/frontend && npm install

# Run the API server
api:
	source .venv/bin/activate && set -a && source .env && set +a && uvicorn src.api.main:app --reload --port 8000

# Run the frontend
frontend:
	cd src/frontend && npm run dev

# Remove venv and cache
clean:
	rm -rf .venv .pytest_cache __pycache__ src/__pycache__ src/api/__pycache__ tests/__pycache__
