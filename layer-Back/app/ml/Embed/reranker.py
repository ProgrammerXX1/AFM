
from sentence_transformers import CrossEncoder
import os

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
reranker = CrossEncoder(RERANKER_MODEL)

def rerank_chunks(query: str, chunks: list[str], top_k: int = 3) -> list[str]:
    pairs = [[query, chunk] for chunk in chunks]
    scores = reranker.predict(pairs)
    scored_chunks = list(zip(chunks, scores))
    ranked = sorted(scored_chunks, key=lambda x: x[1], reverse=True)

    print(f"\n🔍 RERANK: {query}\n{'='*60}")
    for i, (chunk, score) in enumerate(ranked):
        mark = "✅" if i < top_k else "  "
        print(f"{mark} [{score:.3f}] {chunk[:100].strip()}...")

    return [chunk for chunk, _ in ranked[:top_k]]