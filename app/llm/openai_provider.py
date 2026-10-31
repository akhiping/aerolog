from __future__ import annotations

import json
import logging
import os

from .base import LLMProvider
from .tools import tools_for_openai

logger = logging.getLogger(__name__)


class OpenAILLM(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        base_url: str | None = None,
    ):
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError("pip install openai") from exc

        self.model = model
        self.embedding_model = embedding_model
        self._client = AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
        )

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
    ) -> dict:
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools_for_openai() if tools is True else tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception:
            logger.exception("OpenAI API call failed")
            raise

        choice = response.choices[0]
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in choice.message.tool_calls
            ]

        return {
            "content": choice.message.content,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
