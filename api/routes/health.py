from fastapi import APIRouter
from ingestion.indexer import collection_stats

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/stats")
def stats():
    return collection_stats()
