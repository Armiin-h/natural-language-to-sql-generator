"""Ollama chat model factory for the SQL agent."""

from langchain_ollama import ChatOllama

from app.config import Settings, get_settings


def build_chat_model(settings: Settings | None = None) -> ChatOllama:
    """Create a low-temperature ChatOllama client for deterministic SQL work."""
    settings = settings or get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )
