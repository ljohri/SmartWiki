from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://wikijs:changeme@postgres:5432/wikijs"
    wikijs_graphql_url: str = "http://wiki:3000/graphql"
    wikijs_api_token: str = ""
    wikijs_locale: str = "en"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    organizer_api_key: str = ""
    wiki_public_url: str = "http://localhost:3000"
    organizer_public_url: str = "http://localhost:3001"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
