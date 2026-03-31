import os

import pytest
from src.api.torah import ask_torah


def test_missing_api_key_raises_error():
    with pytest.raises(ValueError, match="GOOGLE_API_KEY is not set"):
        ask_torah("What is Shabbat?", api_key=None)


def test_empty_question_raises_error():
    with pytest.raises(ValueError, match="Please enter a question"):
        ask_torah("", api_key="test-key")


def test_whitespace_question_raises_error():
    with pytest.raises(ValueError, match="Please enter a question"):
        ask_torah("   ", api_key="test-key")


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)
def test_basic_question_returns_answer():
    api_key = os.environ["GOOGLE_API_KEY"]
    answer = ask_torah("What is Shabbat?", api_key=api_key)
    assert isinstance(answer, str)
    assert len(answer) > 50


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)
def test_system_prompt_shapes_response():
    api_key = os.environ["GOOGLE_API_KEY"]
    answer = ask_torah("What is Shabbat?", api_key=api_key)
    answer_lower = answer.lower()
    # Should NOT present itself as a rabbi
    assert "i am a rabbi" not in answer_lower
    # Should cite at least one source (Torah, Talmud, Genesis, Exodus, etc.)
    source_keywords = ["torah", "talmud", "genesis", "exodus", "bereishit", "shemot", "mishnah", "gemara"]
    has_source = any(kw in answer_lower for kw in source_keywords)
    assert has_source, f"No source found in answer: {answer[:200]}"


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)
def test_halakhic_question_gets_disclaimer():
    api_key = os.environ["GOOGLE_API_KEY"]
    answer = ask_torah("Can I use my phone on Shabbat?", api_key=api_key)
    answer_lower = answer.lower()
    disclaimer_keywords = ["rabbi", "halakhic authority", "posek", "consult"]
    has_disclaimer = any(kw in answer_lower for kw in disclaimer_keywords)
    assert has_disclaimer, f"No disclaimer found in answer: {answer[:200]}"
