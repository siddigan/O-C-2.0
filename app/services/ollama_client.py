import json

import httpx

from app.core.settings import settings


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model

    def chat_json(self, prompt: str, fallback: dict) -> dict:
        try:
            with httpx.Client(timeout=45) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
                )
                response.raise_for_status()
                payload = response.json().get("response", "{}")
                return json.loads(payload)
        except Exception:
            return fallback
