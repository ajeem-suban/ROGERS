import json
import os
import httpx
from typing import Optional
from .base import AIProvider
from ..models import Blueprint
from .groq_provider import BLUEPRINT_SYSTEM_PROMPT


class OllamaProvider(AIProvider):
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:latest")

    @property
    def name(self) -> str:
        return f"ollama ({self.model})"

    async def generate_blueprint(self, project_name: str, project_idea: str) -> Blueprint:
        user_prompt = f"Project Name: {project_name}\nProject Idea:\n{project_idea}"

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": BLUEPRINT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2}
                }
            )

            if response.status_code != 200:
                raise RuntimeError(f"Ollama error ({response.status_code}): {response.text}")

            result = response.json()
            raw_content = result.get("message", {}).get("content", "")
            parsed = json.loads(raw_content)
            return Blueprint.model_validate(parsed)
