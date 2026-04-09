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

SYSTEM_PROMPT = """You are a chavruta (Torah study partner), NOT a rabbi. Never claim to be a rabbi or a halakhic authority.

Your users are beginners: ba'alei teshuva, French-speaking olim, traditional Jews who never studied texts formally. Explain like you're talking to a curious friend over coffee.

## Rules

1. Answer ONLY based on the sources provided below. Do not use your general knowledge.
2. For each claim, cite the source reference with its Sefaria link.
3. If the sources don't contain relevant information, say: "I didn't find this text in my library yet. Try asking about a different topic or check directly on sefaria.org."
4. For ANY practical halakhic question, add at the end: "This is for learning purposes only. Please consult your Rabbi for a practical ruling."
5. Answer in the same language the user writes in.
6. When quoting Hebrew texts, provide the original Hebrew AND a translation in the user's language.
7. Give detailed explanations of the sources you have. Be a real study partner.
8. At the end, list the sources you used with their Sefaria links.
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
    """Build context string from sources for the LLM prompt."""
    parts = []
    for i, s in enumerate(sources, 1):
        parts.append(f"[Source {i}] {s.ref} ({s.category}, {s.lang})\n{s.text}\nLink: {s.url}")
    return "\n\n".join(parts)


def ask_with_rag(
    question: str,
    gemini_client: genai.Client,
    wv_client: weaviate.WeaviateClient,
    cohere_client: cohere.Client,
) -> str:
    """Full RAG pipeline: search -> rerank -> generate."""
    sources = search(question, gemini_client, wv_client, k=20)
    ranked = rerank(question, sources, cohere_client, top_n=5)
    context = build_context(ranked)

    prompt = f"""Here are the relevant Torah sources:

{context}

Question: {question}"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
        contents=prompt,
    )
    return response.text


def stream_with_rag(
    question: str,
    gemini_client: genai.Client,
    wv_client: weaviate.WeaviateClient,
    cohere_client: cohere.Client,
) -> Generator[str, None, None]:
    """Full RAG pipeline with streaming: search -> rerank -> stream generation."""
    sources = search(question, gemini_client, wv_client, k=20)
    ranked = rerank(question, sources, cohere_client, top_n=5)
    context = build_context(ranked)

    prompt = f"""Here are the relevant Torah sources:

{context}

Question: {question}"""

    response = gemini_client.models.generate_content_stream(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
        contents=prompt,
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text
