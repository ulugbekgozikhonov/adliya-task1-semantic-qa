from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    embed_model: str = "BAAI/bge-m3"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "questions"
    hf_offline: bool = False
    search_threshold: float = 0.65
    search_margin: float = 0.06
    bot_token: str = ""
    api_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
