from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OC2 Local Job Search"
    database_url: str = "sqlite:///./oc2.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    scheduler_enabled: bool = True
    log_level: str = "INFO"
    log_file: str = "logs/oc2.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
