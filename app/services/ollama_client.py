import json

import httpx

from app.core.logging_config import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model

    def chat_json(self, prompt: str, fallback: dict) -> dict:
        try:
            logger.info("ollama.request.start model=%s prompt_chars=%s", self.model, len(prompt))
            with httpx.Client(timeout=45) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
                )
                response.raise_for_status()
                payload = response.json().get("response", "{}")
                parsed = json.loads(payload)
                logger.info("ollama.request.success model=%s", self.model)
                return parsed
        except Exception as exc:
            logger.warning("ollama.request.fallback model=%s error=%s", self.model, str(exc))
            return fallback
