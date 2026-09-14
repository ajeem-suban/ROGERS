import json
import os
import httpx
from typing import Optional
from .base import AIProvider
from ..models import Blueprint, TechStack, Architecture, DevelopmentTask


BLUEPRINT_SYSTEM_PROMPT = """You are ROGERS, an expert AI software architect and technical project manager.
Your task is to take a software project idea and transform it into a practical, production-grade technical blueprint.

CRITICAL INSTRUCTIONS:
- You must return ONLY valid JSON matching this exact structure, with no additional markdown, explanations, or commentary.
- Be practical and engineering-focused for an MVP.
- Avoid overengineering, unnecessary microservices, or bloated infrastructure.

JSON Schema:
{
  "summary": "Concise executive technical summary",
  "requirements": ["Functional requirement 1", "Functional requirement 2"],
  "tech_stack": {
    "frontend": "Frontend framework and styling",
    "backend": "Backend framework and runtime",
    "database": "Primary database and caching",
    "ai": "AI/ML models, libraries, or APIs"
  },
  "architecture": {
    "description": "High-level architecture and data flow",
    "components": ["Component 1", "Component 2", "Component 3"]
  },
  "development_tasks": [
    {
      "title": "Task title",
      "description": "Detailed task description",
      "priority": "high"
    }
  ],
  "next_steps": ["Immediate next step 1", "Immediate next step 2"]
}
"""


class GroqProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def name(self) -> str:
        return f"groq ({self.model})"

    async def generate_blueprint(self, project_name: str, project_idea: str) -> Blueprint:
        if not self.api_key:
            raise ValueError("Groq API key not provided or found in GROQ_API_KEY environment variable.")

        user_prompt = f"Project Name: {project_name}\nProject Idea:\n{project_idea}"

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.endpoint,
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
                raise RuntimeError(f"Groq API error ({response.status_code}): {response.text}")

            result = response.json()
            raw_content = result["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)
            return Blueprint.model_validate(parsed)
