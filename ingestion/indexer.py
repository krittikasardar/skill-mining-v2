"""
ingestion/indexer.py
Upsert embedded chunks into a local persistent Chroma collection.
Idempotent: upsert by chunk ID.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings


_chroma_client: chromadb.PersistentClient | None = None
_collection = None


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> int:
    """
    Upsert chunks into Chroma.

    Args:
        chunks:     list of {id, type, text, metadata} dicts
        embeddings: matching list of embedding vectors

    Returns:
        count of upserted items
    """
    if not chunks:
        return 0

    collection = _get_collection()

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return len(chunks)


def delete_profile(username: str) -> int:
    """Remove all chunks for a username (useful for re-ingestion)."""
    collection = _get_collection()
    results = collection.get(where={"username": username})
    ids = results.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def collection_stats() -> dict:
    """Return basic stats about the indexed collection."""
    collection = _get_collection()
    count = collection.count()
    return {"total_chunks": count, "collection": settings.chroma_collection}


def query_collection(
    query_embedding: list[float],
    n_results: int = 10,
    where: dict | None = None,
    chunk_types: list[str] | None = None,
) -> dict:
    """
    Query Chroma with an embedding vector + optional metadata filters.

    Args:
        query_embedding: embedded query vector
        n_results:       number of results
        where:           Chroma where-filter dict
        chunk_types:     filter to specific chunk types

    Returns:
        Chroma query result dict
    """
    collection = _get_collection()

    # Build where filter
    filters = []
    if where:
        filters.append(where)
    if chunk_types:
        if len(chunk_types) == 1:
            filters.append({"chunk_type": {"$eq": chunk_types[0]}})
        else:
            filters.append({"chunk_type": {"$in": chunk_types}})

    combined_where = None
    if len(filters) == 1:
        combined_where = filters[0]
    elif len(filters) > 1:
        combined_where = {"$and": filters}

    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    if combined_where:
        kwargs["where"] = combined_where

    return collection.query(**kwargs)


def get_profile_chunks(username: str) -> dict:
    """Fetch all chunks for a specific username."""
    collection = _get_collection()
    return collection.get(
        where={"username": username},
        include=["documents", "metadatas"],
    )
