from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "sqlite:///./audit_agent.db"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    # LLM (provider-agnostic via LiteLLM)
    # Used for NL-question -> SQL query generation (needs a strong hosted model).
    LLM_MODEL: str = "gemini/gemini-flash-latest"
    LLM_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 30

    # Used for per-finding audit explanations (runs many times per dataset,
    # so it points at a local Ollama model instead of a rate-limited API).
    FINDINGS_LLM_MODEL: str = "ollama_chat/llama3.1:8b"
    FINDINGS_LLM_API_BASE: str = "http://localhost:11434"
    FINDINGS_LLM_TIMEOUT_SECONDS: int = 60

    # Audit configuration defaults
    MATERIALITY_THRESHOLD: float = 50000
    DORMANT_VENDOR_DAYS: int = 180
    NEW_VENDOR_WINDOW_DAYS: int = 30
    NEW_VENDOR_HIGH_VALUE: float = 10000
    VENDOR_CONCENTRATION_PCT: float = 40
    BENFORD_P_VALUE: float = 0.05
    OUTLIER_ZSCORE_THRESHOLD: float = 3.0
    SPLIT_TRANSACTION_WINDOW_DAYS: int = 1

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True


settings = Settings()
