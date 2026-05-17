"""
config.py — Central settings loaded from .env
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")
    llm_model: str = Field("gpt-4o", env="LLM_MODEL")

    # Chroma
    chroma_persist_dir: str = Field("./chroma_store", env="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field("github_profiles", env="CHROMA_COLLECTION")

    # Data
    data_dir: str = Field("./data", env="DATA_DIR")

    # API
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")

    # LangSmith
    langsmith_tracing: bool = Field(False, env="LANGSMITH_TRACING")
    langsmith_api_key: str = Field("", env="LANGSMITH_API_KEY")
    langsmith_project: str = Field("github-profile-intelligence", env="LANGSMITH_PROJECT")
    langsmith_endpoint: str = Field("https://api.smith.langchain.com", env="LANGSMITH_ENDPOINT")

    # DeepEval / Response Saving
    save_responses: bool = Field(True, env="SAVE_RESPONSES")
    eval_log_dir: str = Field("./eval_logs", env="EVAL_LOG_DIR")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()