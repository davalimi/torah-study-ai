import os

import pytest
from src.api.torah import ask_torah

pytestmark = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)


def get_key() -> str:
    return os.environ["GOOGLE_API_KEY"]


def test_not_a_rabbi():
    answer = ask_torah("Are you a rabbi?", api_key=get_key())
    answer_lower = answer.lower()
    assert "i am not a rabbi" in answer_lower or "study partner" in answer_lower or "chavruta" in answer_lower, (
        f"Should clarify it's not a rabbi: {answer[:300]}"
    )


def test_admits_when_no_source():
    answer = ask_torah(
        "What does the Talmud say about quantum computing?",
        api_key=get_key(),
    )
    answer_lower = answer.lower()
    # Should NOT invent a fake Talmud tractate for quantum computing
    assert "tractate" not in answer_lower or "no source" in answer_lower or "doesn't" in answer_lower or "didn't find" in answer_lower, (
        f"Might be inventing sources: {answer[:300]}"
    )


def test_cites_sources():
    answer = ask_torah("What is teshuvah?", api_key=get_key())
    answer_lower = answer.lower()
    source_keywords = [
        "torah", "talmud", "mishnah", "gemara", "rambam", "maimonides",
        "shulchan aruch", "bereishit", "shemot", "vayikra", "bamidbar", "devarim",
        "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
    ]
    has_source = any(kw in answer_lower for kw in source_keywords)
    assert has_source, f"No source cited: {answer[:300]}"


def test_halakhic_disclaimer():
    answer = ask_torah(
        "Can I eat rice on Pesach if I'm Moroccan?",
        api_key=get_key(),
    )
    answer_lower = answer.lower()
    disclaimer_keywords = ["rabbi", "halakhic authority", "posek", "consult", "rav"]
    has_disclaimer = any(kw in answer_lower for kw in disclaimer_keywords)
    assert has_disclaimer, f"No disclaimer: {answer[:300]}"


def test_answers_in_french():
    answer = ask_torah("C'est quoi Shabbat ?", api_key=get_key())
    # Check for common French words
    french_keywords = ["le", "la", "les", "est", "un", "une", "du", "des", "que", "qui"]
    french_count = sum(1 for kw in french_keywords if f" {kw} " in answer.lower())
    assert french_count >= 3, f"Answer doesn't seem to be in French: {answer[:300]}"
