from __future__ import annotations

import hashlib
import json
import logging
import os
import struct

from .base import LLMProvider
from .tools import tools_for_anthropic

logger = logging.getLogger(__name__)

EMBED_DIM = 128


class AnthropicLLM(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5-20251001",

    ):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise ImportError("pip install anthropic") from exc

        self.model = model
        self._client = AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
    ) -> dict:
        system_msg = None
        api_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                api_messages.append(m)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": api_messages,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if tools:
            kwargs["tools"] = tools_for_anthropic() if tools is True else tools
        if tool_choice:
            if isinstance(tool_choice, str):
                kwargs["tool_choice"] = {"type": tool_choice}
            else:
                kwargs["tool_choice"] = tool_choice

        try:
            response = await self._client.messages.create(**kwargs)
        except Exception:
            logger.exception("Anthropic API call failed")
            raise

        content_text = None
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input,
                    }
                )

        return {
            "content": content_text,
            "tool_calls": tool_calls if tool_calls else None,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Hash-based pseudo-embeddings — Anthropic has no embeddings API.

        For production, swap in a real embedding provider (Voyage, OpenAI, etc.).
        """
        return [self._hash_embed(t) for t in texts]

    @staticmethod
    def _hash_embed(text: str) -> list[float]:
        digest = hashlib.sha512(text.lower().encode()).digest()
        needed = EMBED_DIM * 4
        repeated = digest * (needed // len(digest) + 1)
        floats = list(struct.unpack(f"<{EMBED_DIM}f", repeated[:needed]))
        norm = max(sum(f * f for f in floats) ** 0.5, 1e-9)
        return [f / norm for f in floats]
