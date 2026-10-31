from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from .chunker import ManualChunk, chunk_manual
from .embeddings import LocalEmbedder

logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(self, embedder=None):
        self.embedder = embedder or LocalEmbedder()
        self.chunks: list[ManualChunk] = []
        self.chunk_vectors: np.ndarray | None = None

    async def ingest_directory(self, directory: str) -> int:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning("Manual directory %s does not exist", directory)
            return 0

        all_chunks: list[ManualChunk] = []
        for filepath in sorted(dir_path.glob("*.md")):
            try:
                chunks = chunk_manual(str(filepath))
                all_chunks.extend(chunks)
                logger.info("Ingested %s: %d chunks", filepath.name, len(chunks))
            except Exception:
                logger.exception("Failed to ingest %s", filepath)

        if not all_chunks:
            return 0

        self.chunks = all_chunks
        texts = [c.content for c in self.chunks]
        self.embedder.fit(texts)
        self.chunk_vectors = self.embedder.embed(texts)
        logger.info("RAG index built: %d chunks, vector shape %s", len(self.chunks), self.chunk_vectors.shape)
        return len(self.chunks)

    async def ingest_from_db(self, manual_docs: list) -> int:
        all_chunks: list[ManualChunk] = []
        for doc in manual_docs:
            content = doc.content if hasattr(doc, "content") else str(doc)
            title = doc.title if hasattr(doc, "title") else "Manual"
            ata = doc.ata_chapter if hasattr(doc, "ata_chapter") else ""
            chunk = ManualChunk(
                doc_title=title,
                ata_chapter=ata,
                section="Full Document",
                content=content,
            )
            all_chunks.append(chunk)

        if not all_chunks:
            return 0

        self.chunks.extend(all_chunks)
        texts = [c.content for c in self.chunks]
        self.embedder.fit(texts)
        self.chunk_vectors = self.embedder.embed(texts)
        return len(all_chunks)

    async def search(self, query: str, ata_chapter: str | None = None, top_k: int = 3) -> list[dict]:
        if not self.chunks or self.chunk_vectors is None:
            return []

        query_vec = self.embedder.embed([query])
        scores = self._cosine_similarity(query_vec, self.chunk_vectors)[0]

        if ata_chapter:
            for i, chunk in enumerate(self.chunks):
                if chunk.ata_chapter and chunk.ata_chapter != ata_chapter:
                    scores[i] *= 0.3

        query_lower = query.lower()
        query_keywords = [w for w in query_lower.split() if len(w) > 1]
        for i, chunk in enumerate(self.chunks):
            content_lower = chunk.content.lower()
            match_count = sum(1 for kw in query_keywords if kw in content_lower)
            if match_count > 0:
                scores[i] *= 1.0 + 0.15 * match_count

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.01:
                continue
            chunk = self.chunks[idx]
            results.append({
                "chunk": chunk,
                "score": score,
                "snippet": chunk.content[:500],
                "doc_title": chunk.doc_title,
                "section": chunk.section,
                "ata_chapter": chunk.ata_chapter,
            })

        return results

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
        return a_norm @ b_norm.T
