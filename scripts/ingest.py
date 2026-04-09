"""Embed Sefaria texts with Gemini and index them in Weaviate."""

import base64
import os
import time
import sys

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from datasets import load_dataset
from google import genai


BATCH_SIZE = 100
PAUSE_BETWEEN_BATCHES = 0  # Gemini allows 1500 req/min, no pause needed
COLLECTION_NAME = "SefariaTexts"


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


def create_collection(client: weaviate.WeaviateClient) -> None:
    if client.collections.exists(COLLECTION_NAME):
        print(f"Collection '{COLLECTION_NAME}' already exists. Skipping creation.")
        return

    client.collections.create(
        name=COLLECTION_NAME,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="ref", data_type=DataType.TEXT),
            Property(name="url", data_type=DataType.TEXT),
            Property(name="lang", data_type=DataType.TEXT),
            Property(name="doc_category", data_type=DataType.TEXT),
            Property(name="version_title", data_type=DataType.TEXT),
        ],
    )
    print(f"Created collection '{COLLECTION_NAME}'")


def embed_batch(gemini_client: genai.Client, texts: list[str]) -> list[list[float]]:
    result = gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
    )
    return [e.values for e in result.embeddings]


def ingest_dataset(
    client: weaviate.WeaviateClient,
    gemini_client: genai.Client,
    dataset_name: str,
    lang: str,
    limit: int | None = None,
) -> int:
    print(f"\nLoading {dataset_name}...")
    dataset = load_dataset(dataset_name, split="train")
    total = min(len(dataset), limit) if limit else len(dataset)
    print(f"  {total:,} texts to index")

    collection = client.collections.get(COLLECTION_NAME)
    indexed = 0

    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch = dataset[start:end]

        texts = batch["text"]
        metadatas = batch["metadata"]

        # Skip empty texts
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        if not valid_indices:
            continue

        valid_texts = [texts[i] for i in valid_indices]
        valid_metas = [metadatas[i] for i in valid_indices]

        # Truncate texts longer than 2048 tokens (~8000 chars) for embedding
        truncated_texts = [t[:8000] for t in valid_texts]

        try:
            vectors = embed_batch(gemini_client, truncated_texts)
        except Exception as e:
            print(f"  Embedding error at batch {start}: {e}")
            time.sleep(10)
            continue

        with collection.batch.fixed_size(batch_size=len(valid_texts)) as batch_writer:
            for i, (text, meta, vector) in enumerate(zip(valid_texts, valid_metas, vectors)):
                batch_writer.add_object(
                    properties={
                        "text": text,
                        "ref": meta.get("ref", ""),
                        "url": meta.get("url", ""),
                        "lang": lang,
                        "doc_category": meta.get("docCategory", ""),
                        "version_title": meta.get("versionTitle", ""),
                    },
                    vector=vector,
                )

        indexed += len(valid_texts)

        if start % (BATCH_SIZE * 10) == 0:
            print(f"  {indexed:,} / {total:,} indexed ({indexed * 100 // total}%)")

        time.sleep(PAUSE_BETWEEN_BATCHES)

    print(f"  Done: {indexed:,} texts indexed for {lang}")
    return indexed


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    if limit:
        print(f"Running with limit: {limit:,} texts per dataset")

    wv_client = get_weaviate_client()
    print(f"Connected to Weaviate: {wv_client.is_ready()}")

    gemini_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    create_collection(wv_client)

    total = 0
    total += ingest_dataset(wv_client, gemini_client, "Sefaria/hebrew_library", "he", limit)
    total += ingest_dataset(wv_client, gemini_client, "Sefaria/english_library", "en", limit)

    print(f"\nTotal indexed: {total:,} texts")
    wv_client.close()


if __name__ == "__main__":
    main()
