import os
from .base import AIProvider
from .builtin_provider import BuiltinProvider
from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider


def get_ai_provider() -> AIProvider:
    """
    Resolves the appropriate AI provider based on configuration or environment.
    Defaults to the robust BuiltinProvider for zero-cost, instant, guaranteed execution.
    """
    provider_pref = os.getenv("ROGERS_AI_PROVIDER", "").lower().strip()

    if provider_pref == "groq" or (not provider_pref and os.getenv("GROQ_API_KEY")):
        if os.getenv("GROQ_API_KEY"):
            return GroqProvider()

    if provider_pref == "openai" or (not provider_pref and os.getenv("OPENAI_API_KEY")):
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider()

    if provider_pref == "ollama":
        return OllamaProvider()

    # Default to built-in expert provider
    return BuiltinProvider()
