from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Gateway auth ─────────────────────────────────────────────────────────
    # When required, /v1/* endpoints reject requests whose bearer doesn't match
    # AND that don't supply their own provider key (BYOK mode).
    master_api_key: str = ""
    master_api_key_required: bool = False

    # ── Provider API keys — set whichever you use ────────────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # ── Detector models ──────────────────────────────────────────────────────
    spacy_model: str = "en_core_web_lg"
    injection_model: str = "protectai/deberta-v3-base-prompt-injection-v2"
    injection_threshold: float = Field(default=0.85, ge=0.0, le=1.0)

    # ── Detector toggles ─────────────────────────────────────────────────────
    toxicity_enabled: bool = True
    toxicity_model: str = "original"
    toxicity_threshold_severe: float = Field(default=0.5, ge=0.0, le=1.0)
    toxicity_threshold_high: float = Field(default=0.7, ge=0.0, le=1.0)
    toxicity_threshold_medium: float = Field(default=0.8, ge=0.0, le=1.0)

    # ── Custom HTTP detectors ────────────────────────────────────────────────
    custom_detector_endpoints: str = ""
    custom_detector_secrets: str = ""
    # If false, custom-detector hosts must resolve to public (non-RFC1918) IPs.
    custom_detector_allow_internal: bool = False

    # ── Gateway ──────────────────────────────────────────────────────────────
    gateway_upstream_timeout_seconds: float = 60.0
    log_level: str = "INFO"

    # Default to localhost-only. Operators must opt-in to wider CORS.
    cors_origins: list[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "vscode-webview://*",
    ]

    # Hard cap on request body bytes (DoS guard). Default 2 MiB.
    max_request_bytes: int = Field(default=2 * 1024 * 1024, ge=1024)

    # ── Tool-surface scanning ────────────────────────────────────────────────
    # When true, tool definition descriptions are also scanned for PII/secrets.
    # Off by default: function.parameters JSON schema field names ("email",
    # "phone_number") cause heavy Presidio false-positives.
    scan_tool_defs: bool = Field(default=False, description="Scan tool definition descriptions for PII/secrets")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _coerce_cors(cls, v):
        # Accept bare comma-separated values in addition to JSON list, so
        # CORS_ORIGINS=https://app.example.com,https://x.example.com works
        # without forcing JSON syntax in env vars.
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                return v
            return [o.strip() for o in s.split(",") if o.strip()]
        return v


settings = Settings()
