from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    master_api_key: str = "dev-master-key"

    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/novisentinel"
    redis_url: str = "redis://localhost:6379"

    spacy_model: str = "en_core_web_lg"
    injection_model: str = "protectai/deberta-v3-base-prompt-injection-v2"
    injection_threshold: float = 0.85

    default_rate_limit_rpm: int = 120
    allow_insecure_webhooks: bool = False
    cors_origins: list[str] = ["http://localhost:3001", "http://127.0.0.1:3001"]
    environment: str = "dev"

    toxicity_enabled: bool = True
    toxicity_model: str = "original"
    toxicity_threshold_severe: float = 0.5
    toxicity_threshold_high: float = 0.7
    toxicity_threshold_medium: float = 0.8


settings = Settings()
