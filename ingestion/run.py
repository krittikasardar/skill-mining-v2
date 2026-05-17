"""
ingestion/run.py
Manual ingestion CLI. Standalone from the agent stack.

Usage:
    uv run ingest                          # ingest all JSON in DATA_DIR
    uv run ingest --file path/to/file.json # ingest single file
    uv run ingest --username jakubroztocil # re-ingest specific profile
    uv run ingest --stats                  # show collection stats
    uv run ingest --delete jakubroztocil   # remove profile from index
"""
import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Must happen before importing config-dependent modules
from ingestion.parser import parse_profile_file
from ingestion.enricher import enrich
from ingestion.chunker import build_chunks
from ingestion.embedder import embed_texts
from ingestion.indexer import upsert_chunks, delete_profile, collection_stats
from config import settings


def ingest_file(filepath: Path, force: bool = False) -> dict:
    """Full pipeline for a single JSON file."""
    print(f"  → Parsing   {filepath.name}")
    profile = parse_profile_file(filepath)
    username = profile.get("username", "unknown")

    print(f"  → Enriching @{username}")
    profile = enrich(profile)

    print(f"  → Chunking")
    chunks = build_chunks(profile)
    print(f"     {len(chunks)} chunks produced")

    texts = [c["text"] for c in chunks]
    print(f"  → Embedding ({settings.embedding_model})")
    embeddings = embed_texts(texts)

    print(f"  → Indexing into Chroma")
    count = upsert_chunks(chunks, embeddings)
    print(f"  ✓ {count} chunks upserted for @{username}\n")

    return {"username": username, "chunks": count}


def ingest_directory(data_dir: Path) -> list[dict]:
    files = sorted(data_dir.glob("*_processed_v2.json"))
    if not files:
        # Also accept any .json files
        files = sorted(data_dir.glob("*.json"))
    if not files:
        print(f"No JSON files found in {data_dir}")
        return []

    print(f"Found {len(files)} profile(s) to ingest\n")
    results = []
    for f in files:
        try:
            result = ingest_file(f)
            results.append(result)
        except Exception as e:
            print(f"  ✗ Failed {f.name}: {e}\n")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Profile Intelligence — Ingestion Pipeline"
    )
    parser.add_argument("--file", type=str, help="Path to a single JSON file")
    parser.add_argument("--username", type=str, help="Re-ingest by username (finds file in DATA_DIR)")
    parser.add_argument("--stats", action="store_true", help="Show collection stats and exit")
    parser.add_argument("--delete", type=str, metavar="USERNAME", help="Delete a profile from index")
    parser.add_argument("--data-dir", type=str, help="Override DATA_DIR from .env")

    args = parser.parse_args()

    if args.stats:
        stats = collection_stats()
        print(f"\nChroma Collection: {stats['collection']}")
        print(f"Total chunks: {stats['total_chunks']}")
        return

    if args.delete:
        n = delete_profile(args.delete)
        print(f"Deleted {n} chunks for @{args.delete}")
        return

    data_dir = Path(args.data_dir or settings.data_dir)

    if args.file:
        ingest_file(Path(args.file))
        return

    if args.username:
        # Find file matching username
        candidates = list(data_dir.glob(f"{args.username}*.json"))
        if not candidates:
            print(f"No file found for username: {args.username}")
            sys.exit(1)
        ingest_file(candidates[0])
        return

    # Default: ingest all
    results = ingest_directory(data_dir)
    print(f"\n{'='*40}")
    print(f"Ingestion complete: {len(results)} profile(s) indexed")
    stats = collection_stats()
    print(f"Total chunks in collection: {stats['total_chunks']}")


if __name__ == "__main__":
    main()
