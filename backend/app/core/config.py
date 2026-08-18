from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    database_url: str = "sqlite:///./inbox.db"
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150
    top_k_chunks: int = 4
    min_similarity: float = 0.45


settings = Settings()
