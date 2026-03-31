.PHONY: test test-unit test-all install dev clean

# Run unit tests only (no API calls)
test:
	source .venv/bin/activate && python -m pytest tests/ -v -k "not basic_question and not system_prompt and not halakhic"

# Run all tests (needs GOOGLE_API_KEY in .env)
test-all:
	source .venv/bin/activate && set -a && source .env && set +a && python -m pytest tests/ -v

# Install dependencies
install:
	python3 -m venv .venv
	source .venv/bin/activate && pip install -r requirements.txt

# Run the script manually
dev:
	source .venv/bin/activate && set -a && source .env && set +a && python -m src.api.torah

# Remove venv and cache
clean:
	rm -rf .venv .pytest_cache __pycache__ src/__pycache__ src/api/__pycache__ tests/__pycache__
