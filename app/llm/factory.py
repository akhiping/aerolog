from __future__ import annotations

from .base import LLMProvider


def create_llm_provider(config=None) -> LLMProvider:
    provider_name = "rule_based"
    anthropic_key = ""
    openai_key = ""

    if config:
        provider_name = getattr(config, "llm_provider", None) or (config.get("llm_provider") if isinstance(config, dict) else "rule_based")
        anthropic_key = getattr(config, "anthropic_api_key", None) or (config.get("anthropic_api_key", "") if isinstance(config, dict) else "")
        openai_key = getattr(config, "openai_api_key", None) or (config.get("openai_api_key", "") if isinstance(config, dict) else "")

    if provider_name == "anthropic" and anthropic_key:
        from .anthropic_provider import AnthropicLLM
        return AnthropicLLM(api_key=anthropic_key)

    if provider_name == "openai" and openai_key:
        from .openai_provider import OpenAILLM
        return OpenAILLM(api_key=openai_key)

    from .rule_based import RuleBasedLLM
    return RuleBasedLLM()
