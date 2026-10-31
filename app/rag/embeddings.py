from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """TF-IDF embedder — no external API needed, good enough for demo retrieval."""

    def __init__(self, max_features: int = 512):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.fitted = False

    def fit(self, texts: list[str]) -> None:
        if texts:
            self.vectorizer.fit(texts)
            self.fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self.fitted:
            self.fit(texts)
            return self.vectorizer.transform(texts).toarray().astype(np.float32)
        return self.vectorizer.transform(texts).toarray().astype(np.float32)


class LLMEmbedder:
    """Delegates to the configured LLM provider's ``embed()`` method."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    async def embed(self, texts: list[str]) -> np.ndarray:
        try:
            vectors = await self.llm.embed(texts)
            return np.array(vectors, dtype=np.float32)
        except Exception:
            logger.warning("LLM embedding failed, falling back to local embedder")
            fallback = LocalEmbedder()
            return fallback.embed(texts)
