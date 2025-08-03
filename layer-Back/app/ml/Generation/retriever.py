import os
from typing import List, Dict
from app.core.weaviate_client import client  # ← импорт клиента
from app.ml.Embed.reranker import rerank_chunks
from app.ml.Embed.embedder import get_embedding
from weaviate.classes.query import Filter
from app.ml.Embed.chunker.postprocess import generic_post_process_for_rerank
def hybrid_search(case_id: int, query: str, top_k: int = 15) -> List[Dict]:
    """
    Гибридный поиск: векторный (semantic) + BM25 + reranker.
    Возвращает reranked top-k чанков по смысловой релевантности.
    """

    if not client.is_connected():
        client.connect()

    collection = client.collections.get("Document")
    filter_by_case = Filter.by_property("case_id").equal(case_id)

    # 🔹 1. Semantic search (vector)
    try:
        query_vector = get_embedding(query)
        semantic_results = collection.query.near_vector(
            near=query_vector,
            filters=filter_by_case,
            limit=top_k * 2
        ).objects
        semantic_chunks = [obj.properties for obj in semantic_results]
    except Exception:
        semantic_chunks = []

    # 🔸 2. BM25 fallback
    try:
        bm25_results = collection.query.bm25(
            query=query,
            filters=filter_by_case,
            limit=top_k * 2
        ).objects
        bm25_chunks = [obj.properties for obj in bm25_results]
    except Exception:
        bm25_chunks = []

    # 🔀 3. Объединение и устранение дубликатов по `semantic_hash`
    combined_dict = {}
    for chunk in semantic_chunks + bm25_chunks:
        hash_key = chunk.get("semantic_hash") or chunk.get("hash")
        if hash_key and hash_key not in combined_dict:
            combined_dict[hash_key] = chunk

    combined_chunks = list(combined_dict.values())

    # 🔥 4. Reranking
    # 🧹 Удаление дубликатов и шаблонных чанков до rerank'а
    print(f"\n🧪 Перед фильтрацией: {len(combined_chunks)} чанков")
    filtered_chunks = generic_post_process_for_rerank(combined_chunks)
    print(f"🧪 После фильтрации: {len(filtered_chunks)} чанков")
    # 🧠 Rerank уже очищенных чанков
    for i, chunk in enumerate(filtered_chunks):
        print(f"\n[{i+1}] type={chunk.get('chunk_type')} | text[:200]:\n{chunk['text'][:200]}")
    reranked = rerank_chunks(query, filtered_chunks, top_k=top_k)

    return reranked
