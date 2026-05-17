"""
ingestion/embedder.py
Embed chunk texts. Supports:
  - OpenAI:  text-embedding-3-small / text-embedding-3-large
  - Nomic:   nomic-embed-text-v1.5 (via OpenAI-compatible API)

Returns list of float vectors matching input order.
"""
import time
from typing import Literal
from openai import OpenAI
from config import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Embed a list of texts in batches.
    Returns list of embedding vectors in same order.
    """
    model = settings.embedding_model
    client = _get_client()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # Nomic requires task-type prefix
        if "nomic" in model.lower():
            batch = [f"search_document: {t}" for t in batch]

        response = client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])

        # Respect rate limits on large batches
        if i + batch_size < len(texts):
            time.sleep(0.1)

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single query string (uses query prefix for nomic)."""
    model = settings.embedding_model
    client = _get_client()

    if "nomic" in model.lower():
        text = f"search_query: {text}"

    response = client.embeddings.create(model=model, input=[text])
    return response.data[0].embedding
