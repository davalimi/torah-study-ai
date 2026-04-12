"""Embed Sefaria texts with Gemini and index them in Weaviate. Fast parallel version."""

import base64
import os
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Thread

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from datasets import load_dataset
from google import genai


EMBED_BATCH_SIZE = 100  # Max per Gemini API call
EMBED_WORKERS = 15      # Parallel embedding threads
WV_BATCH_SIZE = 500     # Weaviate batch insert size
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
        print(f"Collection '{COLLECTION_NAME}' exists. Resuming.")
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


def embed_with_retry(gemini_client: genai.Client, texts: list[str], max_retries: int = 5) -> list[list[float]]:
    for attempt in range(max_retries):
        try:
            result = gemini_client.models.embed_content(
                model="gemini-embedding-001",
                contents=texts,
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = min(2 ** attempt + 2, 30)
                time.sleep(wait)
            elif attempt < max_retries - 1:
                time.sleep(1)
            else:
                return []
    return []


def weaviate_writer(wv_client: weaviate.WeaviateClient, queue: Queue, stats: dict) -> None:
    """Background thread that writes to Weaviate from the queue."""
    collection = wv_client.collections.get(COLLECTION_NAME)
    buffer = []

    while True:
        item = queue.get()
        if item is None:
            break

        buffer.extend(item)

        if len(buffer) >= WV_BATCH_SIZE:
            try:
                with collection.batch.fixed_size(batch_size=len(buffer)) as batch:
                    for obj in buffer:
                        batch.add_object(properties=obj["properties"], vector=obj["vector"])
                stats["indexed"] += len(buffer)
            except Exception as e:
                print(f"  Weaviate write error: {e}")
            buffer = []

        queue.task_done()

    if buffer:
        try:
            with collection.batch.fixed_size(batch_size=len(buffer)) as batch:
                for obj in buffer:
                    batch.add_object(properties=obj["properties"], vector=obj["vector"])
            stats["indexed"] += len(buffer)
        except Exception as e:
            print(f"  Weaviate flush error: {e}")


def embed_chunk(gemini_client: genai.Client, texts: list[str], metas: list[dict], lang: str) -> list[dict]:
    """Embed a chunk and return objects ready for Weaviate."""
    valid = [(t, m) for t, m in zip(texts, metas) if t and t.strip()]
    if not valid:
        return []

    valid_texts = [t[:8000] for t, _ in valid]
    valid_metas = [m for _, m in valid]

    vectors = embed_with_retry(gemini_client, valid_texts)
    if not vectors:
        return []

    return [
        {
            "properties": {
                "text": text,
                "ref": meta.get("ref", ""),
                "url": meta.get("url", ""),
                "lang": lang,
                "doc_category": meta.get("docCategory", ""),
                "version_title": meta.get("versionTitle", ""),
            },
            "vector": vector,
        }
        for text, meta, vector in zip([t for t, _ in valid], valid_metas, vectors)
    ]


def ingest_dataset(
    wv_client: weaviate.WeaviateClient,
    gemini_client: genai.Client,
    dataset_name: str,
    lang: str,
    limit: int | None = None,
    start_from: int = 0,
) -> int:
    print(f"\nLoading {dataset_name}...")
    dataset = load_dataset(dataset_name, split="train")
    total = min(len(dataset), limit) if limit else len(dataset)
    actual_total = total - start_from
    print(f"  {actual_total:,} texts to index (from {start_from:,} to {total:,})")

    stats = {"indexed": 0}
    queue: Queue = Queue(maxsize=50)

    writer = Thread(target=weaviate_writer, args=(wv_client, queue, stats), daemon=True)
    writer.start()

    start_time = time.time()

    chunks = []
    for start in range(start_from, total, EMBED_BATCH_SIZE):
        end = min(start + EMBED_BATCH_SIZE, total)
        batch = dataset[start:end]
        chunks.append((batch["text"], batch["metadata"], lang))

    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as pool:
        futures = {
            pool.submit(embed_chunk, gemini_client, texts, metas, lng): i
            for i, (texts, metas, lng) in enumerate(chunks)
        }

        done_count = 0
        for future in as_completed(futures):
            try:
                objects = future.result()
                if objects:
                    queue.put(objects)
            except Exception as e:
                print(f"  Error: {e}")

            done_count += 1
            if done_count % 50 == 0:
                elapsed = time.time() - start_time
                rate = stats["indexed"] / elapsed if elapsed > 0 else 0
                eta = (actual_total - stats["indexed"]) / rate / 3600 if rate > 0 else 0
                print(f"  {stats['indexed']:,} / {actual_total:,} ({stats['indexed'] * 100 // max(actual_total, 1)}%) - {rate:.0f}/sec - ETA: {eta:.1f}h", flush=True)

    queue.put(None)
    writer.join()

    print(f"  Done: {stats['indexed']:,} texts for {lang}")
    return stats["indexed"]


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    start_from = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    if limit:
        print(f"Limit: {limit:,} per dataset")
    if start_from:
        print(f"Starting from: {start_from:,}")

    wv_client = get_weaviate_client()
    print(f"Connected: {wv_client.is_ready()}")

    if wv_client.collections.exists(COLLECTION_NAME):
        count = wv_client.collections.get(COLLECTION_NAME).aggregate.over_all(total_count=True)
        print(f"Already indexed: {count.total_count:,}")

    gemini_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    create_collection(wv_client)

    total = 0
    # English only - cheaper and more accessible for beginners
    total += ingest_dataset(wv_client, gemini_client, "Sefaria/english_library", "en", limit, start_from)

    print(f"\nTotal new: {total:,}")
    wv_client.close()


if __name__ == "__main__":
    main()
