from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Superannuation Advisory Intelligence API"
    demo_mode: bool = True
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8081",
    ]
    max_iterations: int = 3

    # LLM (server-side only; never sent to the browser)
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-5"
    use_real_llm: bool = False

    # Persistence: SQLite file by default, postgresql+psycopg://... in docker-compose
    database_url: str = "sqlite:///./data/advisory.db"

    # Hybrid retrieval. "mock" keeps tests offline and fast.
    retrieval_backend: Literal["hybrid", "mock"] = "hybrid"
    models_dir: str = "./data/models"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    qdrant_url: str | None = None  # e.g. http://localhost:56333; embedded local store when unset
    qdrant_path: str = "./data/qdrant"
    qdrant_collection: str = "superannuation_documents"
    neo4j_uri: str | None = None  # e.g. bolt://localhost:57687; in-process networkx graph when unset
    neo4j_user: str = "neo4j"
    neo4j_password: str | None = None

    # Authentication
    auth_enabled: bool = True
    jwt_secret: str | None = None  # random per-process secret when unset (tokens reset on restart)
    jwt_expiry_minutes: int = 480
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None

    rate_limit_enabled: bool = False


settings = Settings()
