"""RAG pipeline using LangChain: hybrid search -> Cohere rerank -> Gemini generation."""

import base64
import os
from collections.abc import Generator
from dataclasses import dataclass

import cohere
import weaviate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


COLLECTION_NAME = "SefariaTexts"

RELEVANCE_THRESHOLD = 0.3  # Cohere rerank score below this = not relevant enough
HYBRID_ALPHA = 0.5  # 0.0 = pure BM25 (keywords), 1.0 = pure vector (meaning), 0.5 = balanced

SYSTEM_PROMPT = """You are a chavruta (Torah study partner), NOT a rabbi.

Answer in the same language the user writes in. Use real Torah sources from the Sefaria library to explain clearly.

## Output format (STRICTLY FOLLOW THIS STRUCTURE)

Your response MUST have these sections, in this order, using Markdown:

### TL;DR

One sentence that directly answers the question. No preamble, no "Great question!". Just the answer.

### Sources

List each relevant source on its own line as a Markdown bullet. Format:
- **[Reference]**: Short quote or paraphrase from the source.

Example:
- **Berakhot 17b:13**: Those before the bier are exempt from reciting Shema.
- **Mishneh Torah, Prayer 6:10**: The Amidah requires greater concentration than the Shema.

### Explanation

A clear explanation in 2-4 paragraphs that synthesizes the sources above and answers the question in depth. Use Markdown for emphasis when needed (**bold**, *italic*).

## Rules

1. Answer ONLY based on the sources provided below. Do not use your general knowledge.
2. Never invent a source or a quote. If a source is not in the provided list, do not cite it.
3. For any practical halakhic question, add at the end after the Explanation section: "*This is for learning purposes only. Please consult your Rabbi for a practical ruling.*"
4. Do NOT paste raw URLs. Just use the reference name in the bullet list.
5. When quoting Hebrew, provide the Hebrew text AND a translation right after.
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


def build_context(sources: list[Source]) -> str:
    """Build context string from sources for the LLM prompt. No URLs - just ref and text."""
    parts = []
    for i, s in enumerate(sources, 1):
        parts.append(f"[Source {i}] {s.ref}\n{s.text}")
    return "\n\n".join(parts)


def build_suggestions(sources: list[Source]) -> str:
    """Build a list of available sources to suggest."""
    seen = set()
    suggestions = []
    for s in sources:
        if s.ref not in seen and len(suggestions) < 5:
            seen.add(s.ref)
            suggestions.append(f"- {s.ref} ({s.category}) - {s.url}")
    return "\n".join(suggestions)


class RAGPipeline:
    """LangChain-based RAG pipeline: hybrid search -> rerank -> generate.

    Components:
    - GoogleGenerativeAIEmbeddings: embed queries for vector search
    - ChatGoogleGenerativeAI: generate answers from sources
    - CohereRerank: re-score retrieved documents
    - LCEL chains: prompt | llm | parser
    """

    def __init__(self, wv_client: weaviate.WeaviateClient) -> None:
        self.wv_client = wv_client

        # 1. Embedding model (same model used to index the 94K texts)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
        )

        # 2. LLM for generation
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
        )

        # 3. Cohere client for reranking (raw client for score access)
        self.cohere_client = cohere.Client(
            api_key=os.environ.get("COHERE_API_KEY", ""),
        )

        # 4. Output parser (converts AIMessage to plain string)
        self.parser = StrOutputParser()

        # 5. LCEL chains: prompt | llm | parser
        #    Each chain gets .invoke() and .stream() for free
        self.rag_chain = (
            ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", "Here are the relevant Torah sources:\n\n{context}\n\nQuestion: {question}"),
            ])
            | self.llm
            | self.parser
        )

        self.fallback_chain = (
            ChatPromptTemplate.from_messages([
                ("system", FALLBACK_PROMPT),
                ("human", "{question}"),
            ])
            | self.llm
            | self.parser
        )

    def _retrieve_and_rerank(self, question: str) -> tuple[list[Source], bool]:
        """Step 1+2: Hybrid search Weaviate -> Cohere rerank -> threshold check.

        Returns (ranked_sources, is_relevant).
        We use raw clients here because:
        - langchain-weaviate doesn't fully support hybrid search
        - We need Cohere scores for threshold gating
        """
        # Embed the question using LangChain's embedding model
        query_vector = self.embeddings.embed_query(question)

        # Hybrid search using raw Weaviate client
        collection = self.wv_client.collections.get(COLLECTION_NAME)
        results = collection.query.hybrid(
            query=question,
            vector=query_vector,
            alpha=HYBRID_ALPHA,
            limit=20,
            return_properties=["text", "ref", "url", "lang", "doc_category"],
        )

        sources = [
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

        if not sources:
            return [], False

        # Rerank with Cohere (raw client for score access)
        response = self.cohere_client.rerank(
            model="rerank-english-v3.0",
            query=question,
            documents=[s.text for s in sources],
            top_n=5,
        )

        ranked = [
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

        return ranked, ranked[0].score >= RELEVANCE_THRESHOLD

    def ask(self, question: str) -> str:
        """Full RAG: search -> rerank -> generate (sync)."""
        ranked, is_relevant = self._retrieve_and_rerank(question)

        if is_relevant:
            context = build_context(ranked)
            return self.rag_chain.invoke({"context": context, "question": question})

        suggestions = build_suggestions(ranked)
        return self.fallback_chain.invoke({"suggestions": suggestions, "question": question})

    def stream(self, question: str) -> Generator[str, None, None]:
        """Full RAG: search -> rerank -> stream generation."""
        ranked, is_relevant = self._retrieve_and_rerank(question)

        if is_relevant:
            context = build_context(ranked)
            for chunk in self.rag_chain.stream({"context": context, "question": question}):
                yield chunk
        else:
            suggestions = build_suggestions(ranked)
            for chunk in self.fallback_chain.stream({"suggestions": suggestions, "question": question}):
                yield chunk
