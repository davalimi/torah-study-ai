"""RAG pipeline: search Weaviate -> rerank with Cohere -> generate with Gemini."""

import base64
import os
from collections.abc import Generator
from dataclasses import dataclass

import cohere
import weaviate
from google import genai
from google.genai import types


COLLECTION_NAME = "SefariaTexts"

RELEVANCE_THRESHOLD = 0.3  # Cohere rerank score below this = not relevant enough

SYSTEM_PROMPT = """You are a chavruta (Torah study partner), NOT a rabbi.

Explain clearly and simply. Adapt to the user's level based on how they ask their question. Answer in the same language the user writes in.

## How to answer

You receive real Torah sources from the Sefaria library. Your job is to READ them, UNDERSTAND them, and EXPLAIN them clearly to the user.

Do NOT just list links or references. Actually explain what the texts say. Quote the important parts directly. Put the source reference in parentheses after the quote, like a book: (Siddur Ashkenaz, Shacharit, Netilat Yadayim 1).

When quoting Hebrew, provide the Hebrew text AND a translation.

Structure your answer like a study session:
- Start with a clear explanation of the topic
- Quote the relevant passages from the sources
- Explain what they mean
- Connect the ideas together

## Rules

1. Answer ONLY based on the sources provided below. Do not use your general knowledge.
2. Never invent a source or a quote.
3. For ANY practical halakhic question, add at the end: "This is for learning purposes only. Please consult your Rabbi for a practical ruling."
4. Do NOT paste raw URLs in your answer. Just cite the reference name in parentheses.
"""

FALLBACK_PROMPT = """You are a chavruta (Torah study partner). The user asked a question but the relevant sources were not found in the library.

Your job is to:
1. Acknowledge that you don't have the exact text in your library yet
2. Build a direct Sefaria link for what they're looking for (use the format https://www.sefaria.org/REFERENCE)
3. Suggest 3 related topics from the sources you DO have (listed below)
4. Answer in the same language the user writes in
5. Be warm and helpful, like a study partner who says "I don't have that book on my shelf, but here's where to find it and here's what I can help you with"

Available sources you can suggest (these are texts you DO have):
{suggestions}
"""


@dataclass(frozen=True)
class Source:
    ref: str
    url: str
    text: str
    lang: str
    category: str
    score: float


def get_weaviate_client() -> weaviate.WeaviateClient:
    host = os.environ["WEAVIATE_URL"].replace("https://", "").replace("http://", "")
    username = os.environ["WEAVIATE_USERNAME"]
    password = os.environ["WEAVIATE_PASSWORD"]
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()

    return weaviate.connect_to_custom(
        http_host=host,
        http_port=443,
        http_secure=True,
        grpc_host=host,
        grpc_port=50052,
        grpc_secure=True,
        headers={"Authorization": f"Basic {credentials}"},
        skip_init_checks=True,
    )


def search(query: str, gemini_client: genai.Client, wv_client: weaviate.WeaviateClient, k: int = 20) -> list[Source]:
    """Step 1: Embed query and search Weaviate for similar texts."""
    result = gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=query,
    )
    query_vector = result.embeddings[0].values

    collection = wv_client.collections.get(COLLECTION_NAME)
    results = collection.query.near_vector(
        near_vector=query_vector,
        limit=k,
        return_properties=["text", "ref", "url", "lang", "doc_category"],
    )

    return [
        Source(
            ref=obj.properties["ref"],
            url=obj.properties["url"],
            text=obj.properties["text"],
            lang=obj.properties["lang"],
            category=obj.properties["doc_category"],
            score=0.0,
        )
        for obj in results.objects
    ]


def rerank(query: str, sources: list[Source], cohere_client: cohere.Client, top_n: int = 5) -> list[Source]:
    """Step 2: Rerank sources with Cohere for better relevance."""
    if not sources:
        return []

    response = cohere_client.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=[s.text for s in sources],
        top_n=top_n,
    )

    return [
        Source(
            ref=sources[r.index].ref,
            url=sources[r.index].url,
            text=sources[r.index].text,
            lang=sources[r.index].lang,
            category=sources[r.index].category,
            score=r.relevance_score,
        )
        for r in response.results
    ]


def build_context(sources: list[Source]) -> str:
    """Build context string from sources for the LLM prompt. No URLs - just ref and text."""
    parts = []
    for i, s in enumerate(sources, 1):
        parts.append(f"[Source {i}] {s.ref}\n{s.text}")
    return "\n\n".join(parts)


def has_relevant_sources(ranked: list[Source]) -> bool:
    """Check if the top reranked source is relevant enough."""
    if not ranked:
        return False
    return ranked[0].score >= RELEVANCE_THRESHOLD


def build_suggestions(sources: list[Source]) -> str:
    """Build a list of available sources to suggest."""
    seen = set()
    suggestions = []
    for s in sources:
        if s.ref not in seen and len(suggestions) < 5:
            seen.add(s.ref)
            suggestions.append(f"- {s.ref} ({s.category}) - {s.url}")
    return "\n".join(suggestions)


def _generate(
    gemini_client: genai.Client,
    system: str,
    prompt: str,
) -> str:
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=system),
        contents=prompt,
    )
    return response.text


def _stream(
    gemini_client: genai.Client,
    system: str,
    prompt: str,
) -> Generator[str, None, None]:
    response = gemini_client.models.generate_content_stream(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=system),
        contents=prompt,
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text


def ask_with_rag(
    question: str,
    gemini_client: genai.Client,
    wv_client: weaviate.WeaviateClient,
    cohere_client: cohere.Client,
) -> str:
    """Full RAG pipeline: search -> rerank -> generate."""
    sources = search(question, gemini_client, wv_client, k=20)
    ranked = rerank(question, sources, cohere_client, top_n=5)

    if has_relevant_sources(ranked):
        context = build_context(ranked)
        prompt = f"Here are the relevant Torah sources:\n\n{context}\n\nQuestion: {question}"
        return _generate(gemini_client, SYSTEM_PROMPT, prompt)

    # Fallback: suggest related topics
    suggestions = build_suggestions(sources)
    system = FALLBACK_PROMPT.format(suggestions=suggestions)
    return _generate(gemini_client, system, question)


def stream_with_rag(
    question: str,
    gemini_client: genai.Client,
    wv_client: weaviate.WeaviateClient,
    cohere_client: cohere.Client,
) -> Generator[str, None, None]:
    """Full RAG pipeline with streaming: search -> rerank -> stream generation."""
    sources = search(question, gemini_client, wv_client, k=20)
    ranked = rerank(question, sources, cohere_client, top_n=5)

    if has_relevant_sources(ranked):
        context = build_context(ranked)
        prompt = f"Here are the relevant Torah sources:\n\n{context}\n\nQuestion: {question}"
        yield from _stream(gemini_client, SYSTEM_PROMPT, prompt)
    else:
        # Fallback: suggest related topics
        suggestions = build_suggestions(sources)
        system = FALLBACK_PROMPT.format(suggestions=suggestions)
        yield from _stream(gemini_client, system, question)
