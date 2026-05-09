from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


def _decrypt_fernet_secret(encrypted_value: str, key: str) -> str:
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError("Install cryptography to use encrypted secrets.") from exc

    return Fernet(key.encode("utf-8")).decrypt(encrypted_value.encode("utf-8")).decode("utf-8")


class Settings(BaseSettings):
    app_name: str = "OC2 Local Job Search"
    database_url: str = "sqlite:///./oc2.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    scheduler_enabled: bool = True
    log_level: str = "INFO"
    log_file: str = "logs/oc2.log"
    firecrawl_api_key: SecretStr | None = None
    firecrawl_api_key_encrypted: str | None = None
    firecrawl_secret_key: SecretStr | None = None
    firecrawl_search_limit: int = 8
    firecrawl_country: str = "IN"
    firecrawl_location: str = "India"
    firecrawl_location_terms: str = "India,Bengaluru,Bangalore,Hyderabad,Pune,Chennai,Mumbai,Gurugram,Gurgaon,Noida"
    firecrawl_timeout_ms: int = 60000
    search_batch_size: int = 45
    search_allow_sample_fallback: bool = False
    job_report_to_email: str = "2001siddi@gmail.com"
    job_report_after_search: bool = True
    job_report_on_shutdown: bool = True
    smtp_host: str | None = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_starttls: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def resolved_firecrawl_api_key(self) -> str | None:
        if self.firecrawl_api_key:
            return self.firecrawl_api_key.get_secret_value()

        if self.firecrawl_api_key_encrypted and self.firecrawl_secret_key:
            return _decrypt_fernet_secret(
                self.firecrawl_api_key_encrypted,
                self.firecrawl_secret_key.get_secret_value(),
            )

        return None


settings = Settings()
