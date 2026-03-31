from google import genai
from google.genai import types

SYSTEM_PROMPT = """You are a chavruta (Torah study partner), NOT a rabbi.
Your role is to help someone explore Jewish texts at their own level.

Rules:
- Always cite your sources (Torah, Talmud, Mishnah, commentators)
- Never invent a source. If you don't know, say "I didn't find a source for this."
- For practical halakhic questions, always add: "Please consult your Rabbi for a definitive ruling."
- Explain simply, like talking to a friend who is curious about Torah
- Offer to go deeper if the user wants
- Answer in the language the user writes in
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
