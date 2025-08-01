import logging
import traceback
from app.core.weaviate_client import save_to_weaviate, client
from app.ml.Embed.smart_chunk import smart_chunk_document
from app.ml.Embed.embedder import get_embedding
from weaviate.classes.query import Filter
from app.ml.Embed.reranker import rerank_chunks

import hashlib
# 🧠 Глобальный кэш всех чанков (в пределах одного запуска)
GLOBAL_CHUNK_HASHES = set()

logger = logging.getLogger(__name__)

def hash_chunk(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

def index_full_document(
    title: str,
    text: str,
    filetype: str,
    user_id: int,
    case_id: int,
    document_id: int,
    doc_type: str
):
    try:
        chunks = smart_chunk_document(
            text=text,
            case_id=case_id,
            document_id=document_id,
            doc_type=doc_type
        )

        logger.info(f"📄 Документ '{title}' разбит на {len(chunks)} чанков (до глобальной фильтрации).")

        for i, chunk in enumerate(chunks):
            chunk_text = chunk["text"]
            chunk_hash = hash_chunk(chunk_text)

            if chunk_hash in GLOBAL_CHUNK_HASHES:
                logger.warning(f"⚠️ Пропущен глобальный дубликат чанка {i + 1}")
                continue

            GLOBAL_CHUNK_HASHES.add(chunk_hash)

            vector = get_embedding(chunk_text)
            if not vector:
                logger.warning(f"⚠️ Пропущен пустой эмбеддинг для чанка {i + 1}")
                continue

            save_to_weaviate(
                title=f"{title}_chunk_{i + 1}",
                text=chunk_text,
                filetype=filetype,
                case_id=case_id,
                document_id=document_id,
                user_id=user_id,
                vector=vector
            )

    except Exception as e:
        logger.error(f"❌ Ошибка индексации документа '{title}': {str(e)}\n{traceback.format_exc()}")
        raise


def search_similar_chunks(query: str, case_id: int, k: int = 5) -> list[dict]:
    """
    Поиск по Weaviate + reranking.
    """
    try:
        if not client.is_connected():
            logger.info("🔌 Подключаемся к Weaviate...")
            client.connect()

        question_vector = get_embedding(query)

        collection = client.collections.get("Document")
        result = collection.query.near_vector(
            near_vector=question_vector,
            filters=Filter.by_property("case_id").equal(case_id),
            limit=15
        )

        raw_results = result.objects
        if not raw_results:
            logger.warning(f"⚠️ Нет кандидатов по запросу: '{query}'")
            return []

        text_to_obj = {}
        for obj in raw_results:
            text = obj.properties.get("text")
            if text and text not in text_to_obj:
                text_to_obj[text] = obj.properties

        unique_texts = list(text_to_obj.keys())
        top_chunks = rerank_chunks(query, unique_texts, top_k=k)
        reranked_matches = [text_to_obj[text] for text in top_chunks if text in text_to_obj]

        logger.info(f"🔍 После reranking отобрано {len(reranked_matches)} чанков для запроса: '{query}'")
        return reranked_matches

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске чанков: {str(e)}\n{traceback.format_exc()}")
        return []
