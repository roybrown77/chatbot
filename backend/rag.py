from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CONTEXT_DIR = Path(__file__).resolve().parent / "context"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
TOP_K = 3
MIN_SCORE = 0.25


class RagStore:
    def __init__(self) -> None:
        self._model = SentenceTransformer("all-MiniLM-L6-v2")
        self._chunks: list[str] = []
        self._embeddings: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        texts: list[str] = []
        for path in sorted(CONTEXT_DIR.glob("*.md")):
            texts.append(path.read_text(encoding="utf-8"))
        self._chunks = _chunk_text("\n\n".join(texts))
        if not self._chunks:
            self._chunks = ["No knowledge base loaded."]
        emb = self._model.encode(self._chunks, normalize_embeddings=True)
        self._embeddings = np.asarray(emb, dtype=np.float32)

    def retrieve(self, query: str) -> list[tuple[str, float]]:
        if self._embeddings is None or not self._chunks:
            return []
        q = self._model.encode([query], normalize_embeddings=True)
        q_vec = np.asarray(q[0], dtype=np.float32)
        scores = self._embeddings @ q_vec
        ranked = sorted(
            zip(self._chunks, scores.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )[:TOP_K]
        return [(chunk, float(score)) for chunk, score in ranked if score >= MIN_SCORE]

    def format_context(self, hits: list[tuple[str, float]]) -> str:
        if not hits:
            return "(No relevant passages found in the knowledge base.)"
        parts = []
        for i, (chunk, score) in enumerate(hits, 1):
            parts.append(f"[{i}] (relevance {score:.2f})\n{chunk}")
        return "\n\n".join(parts)


def _chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start, end)
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks
