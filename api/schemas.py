"""
api/schemas.py
Pydantic models for FastAPI request/response.
"""
from pydantic import BaseModel, Field
from typing import Literal, Any


class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    agent_version: Literal["v1", "v2"] = Field("v1", description="Agent version to use")
    chat_history: list[dict] = Field(default_factory=list, description="Prior conversation turns (V1 only)")


class ProfileRequest(BaseModel):
    username: str = Field(..., description="GitHub username for deep dive")
    agent_version: Literal["v1", "v2"] = Field("v1")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Role/skills requirement query")
    agent_version: Literal["v1", "v2"] = Field("v1")
    min_experience_years: int = Field(0, ge=0)
    required_language: str = Field("", description="Filter by primary language")
    seniority_tier: Literal["", "junior", "mid", "senior", "staff"] = ""
    has_leadership: bool = False


class AgentResponse(BaseModel):
    mode: str
    output: str
    agent_version: str
    latency_seconds: float
    username: str | None = None
    intermediate_steps: list[dict] = Field(default_factory=list)
    pipeline_trace: list[dict] = Field(default_factory=list)
    error: str | None = None


class StatsResponse(BaseModel):
    total_chunks: int
    collection: str


class IngestResponse(BaseModel):
    status: str
    files_processed: int
    total_chunks_upserted: int
    errors: list[str] = Field(default_factory=list)
