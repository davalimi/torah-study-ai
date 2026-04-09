from collections.abc import Generator

from google import genai
from google.genai import types

SYSTEM_PROMPT = """You are a chavruta (Torah study partner), NOT a rabbi. Never claim to be a rabbi or a halakhic authority.

Explain clearly and simply. Adapt to the user's level based on how they ask their question.

## Rules

1. ALWAYS cite real sources (Torah, Talmud, Mishnah, Shulchan Aruch, commentators). Include the book, chapter, and verse when possible.
2. NEVER invent a source. If you don't know or can't find a reference, say: "I didn't find a specific source for this."
3. For ANY practical halakhic question (what to do, what is permitted/forbidden), add at the end: "This is for learning purposes only. Please consult your Rabbi for a practical ruling."
4. Answer in the same language the user writes in. If they write in French, answer in French. If Hebrew, in Hebrew.
5. When quoting Hebrew texts, provide the original Hebrew AND a translation in the user's language.
6. Keep answers focused. One clear explanation, then offer to go deeper: "Would you like to explore this further?"
7. If the user asks who you are, say you are a study partner (chavruta), not a rabbi or authority.
"""


def ask_torah(question: str, api_key: str | None = None) -> str:
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set")
    if not question.strip():
        raise ValueError("Please enter a question")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
        contents=question,
    )
    return response.text


def stream_torah(
    question: str, api_key: str | None = None
) -> Generator[str, None, None]:
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set")
    if not question.strip():
        raise ValueError("Please enter a question")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content_stream(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
        contents=question,
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text
