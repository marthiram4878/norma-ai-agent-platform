"""LLM provider composition without agent or prompt business logic."""

from openai import AsyncOpenAI

from app.core.config import Settings, settings


class OpenRouterConfigurationError(RuntimeError):
    """Raised when OpenRouter is requested without credentials."""


def create_openrouter_client(config: Settings = settings) -> AsyncOpenAI:
    """Build an OpenAI-compatible client configured for OpenRouter."""

    if config.openrouter_api_key is None:
        raise OpenRouterConfigurationError("OPENROUTER_API_KEY is not configured")

    return AsyncOpenAI(
        api_key=config.openrouter_api_key.get_secret_value(),
        base_url=config.openrouter_base_url,
        default_headers={"X-Title": config.app_name},
    )
