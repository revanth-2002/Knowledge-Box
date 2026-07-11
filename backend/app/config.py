"""Centralized application configuration.

All tunable behavior (models, chunking, storage location) lives here so the
rest of the codebase never reads os.environ directly.
"""
from functools import lru_cache
from dotenv import load_dotenv
import os

load_dotenv()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM providers ---
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    embedding_dimensions: int = 768
    chat_model: str = os.getenv("CHAT_MODEL", "gemini-3.1-flash-lite")

    # --- Storage ---
    database_url: str = "sqlite:///./knowledge_inbox.db"

    # --- Chunking ---
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50

    # --- Retrieval ---
    top_k_chunks: int = 5
    max_similarity_candidates: int = 2000  # brute-force scan cap, see vector_store.py

    # --- Fetching ---
    fetch_timeout_seconds: float = 10.0
    max_fetch_bytes: int = 3_000_000  # 3MB cap on downloaded pages

    # --- App ---
    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
