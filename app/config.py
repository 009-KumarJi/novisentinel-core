from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Provider API keys — set whichever you use
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Detector models
    spacy_model: str = "en_core_web_lg"
    injection_model: str = "protectai/deberta-v3-base-prompt-injection-v2"
    injection_threshold: float = 0.85

    # Detector toggles
    toxicity_enabled: bool = True
    toxicity_model: str = "original"
    toxicity_threshold_severe: float = 0.5
    toxicity_threshold_high: float = 0.7
    toxicity_threshold_medium: float = 0.8

    # Custom HTTP detectors (comma-separated URLs and optional secrets)
    custom_detector_endpoints: str = ""
    custom_detector_secrets: str = ""

    # Gateway
    gateway_upstream_timeout_seconds: float = 60.0
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]


settings = Settings()
