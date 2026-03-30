from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    wikijs_graphql_url: str = "http://wiki:3000/graphql"
    wikijs_api_token: str = ""
    wikijs_locale: str = "en"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    voyageai_api_key: str = ""
    voyage_embedding_model: str = "voyage-4"
    voyage_embedding_dimension: int = 1024
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "wiki_chunks"
    chatbot_api_key: str = ""
    wiki_public_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    ingest_interval_seconds: int = 21600
    chat_rate_limit_per_minute: int = 20


settings = Settings()
