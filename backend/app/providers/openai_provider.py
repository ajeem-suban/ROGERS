import json
import os
import httpx
from typing import Optional
from .base import AIProvider
from ..models import Blueprint
from .groq_provider import BLUEPRINT_SYSTEM_PROMPT


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def name(self) -> str:
        return f"openai ({self.model})"

    async def generate_blueprint(self, project_name: str, project_idea: str) -> Blueprint:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured.")

        user_prompt = f"Project Name: {project_name}\nProject Idea:\n{project_idea}"

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": BLUEPRINT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                }
            )

            if response.status_code != 200:
                raise RuntimeError(f"OpenAI API error ({response.status_code}): {response.text}")

            result = response.json()
            raw_content = result["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)
            return Blueprint.model_validate(parsed)
