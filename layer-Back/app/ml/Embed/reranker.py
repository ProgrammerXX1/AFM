from sentence_transformers import CrossEncoder
import os
import logging

logger = logging.getLogger(__name__)

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
reranker = CrossEncoder(RERANKER_MODEL)


def rerank_chunks(query: str, chunks: list[dict], top_k: int = 3) -> list[dict]:
    """
    Переоценка чанков по смысловой релевантности. Возвращает top-k чанков (dict).
    Используется CrossEncoder reranker (например, BAAI/bge-reranker-base).
    """

    filtered_pairs = []
    valid_chunks = []

    for i, chunk in enumerate(chunks):
        if not isinstance(chunk, dict) or "text" not in chunk:
            logger.warning(f"❗ Пропущен невалидный чанк [{i}]: {type(chunk)}")
            continue
        text = chunk["text"].strip()
        if not text:
            continue
        filtered_pairs.append([query, text])
        valid_chunks.append(chunk)

    if not filtered_pairs:
        logger.warning("⚠️ Нет валидных чанков для rerank.")
        return []

    # 🔥 Оценка релевантности
    scores = reranker.predict(filtered_pairs)
    scored_chunks = list(zip(valid_chunks, scores))

    # Сортировка по убыванию
    ranked = sorted(scored_chunks, key=lambda x: x[1], reverse=True)

    print(f"\n🔍 RERANK: {query}\n{'=' * 60}")
    for i, (chunk, score) in enumerate(ranked):
        mark = "✅" if i < top_k else "  "
        preview = chunk.get("text", "")[:100].strip().replace("\n", " ")
        print(f"{mark} [{score:.3f}] {preview}...")

    return [chunk for chunk, _ in ranked[:top_k]]
