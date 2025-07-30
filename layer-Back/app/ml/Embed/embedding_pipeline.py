import logging
import traceback

from app.core.weaviate_client import save_to_weaviate, client
from app.ml.Embed.embedder import get_embedding
from app.ml.Embed.chunker import smart_chunk_document  # ← твой умный чанкер
from weaviate.classes.query import Filter
from app.ml.Embed.reranker import rerank_chunks  # ✅ подключаем локальный reranker

logger = logging.getLogger(__name__)

def index_full_document(
    title: str,
    text: str,
    filetype: str,
    user_id: int,
    case_id: int,
    document_id: int  # ❗️Теперь обязательный аргумент
):
    """Индексация документа с разбиением на смысловые чанки и сохранением в Weaviate."""
    try:
        chunks = smart_chunk_document(
            text=text,
            user_id=user_id,
            case_id=case_id,
            document_id=document_id,  # ✅ передаём обязательно
            global_dedup=True
        )
        logger.info(f"📄 Документ '{title}' разбит на {len(chunks)} смысловых чанков.")

        for i, chunk in enumerate(chunks):
            try:
                vector = get_embedding(chunk)
                if not vector:
                    logger.warning(f"⚠️ Пропущен пустой эмбеддинг для чанка {i+1}")
                    continue

                save_to_weaviate(
                    title=f"{title}_chunk_{i+1}",
                    text=chunk,
                    filetype=filetype,
                    case_id=case_id,
                    vector=vector,
                    document_id=document_id
                )
            except Exception as e:
                logger.error(f"❌ Ошибка при индексации чанка {i+1} файла '{title}': {str(e)}\n{traceback.format_exc()}")
                continue

    except Exception as e:
        logger.error(f"❌ Ошибка индексации документа '{title}': {str(e)}\n{traceback.format_exc()}")
        raise

def search_similar_chunks(query: str, case_id: int, k: int = 5) -> list[dict]:
    """Поиск релевантных чанков по запросу с reranking внутри дела (по case_id)."""
    try:
        if not client.is_connected():
            logger.info("🔌 Подключаемся к Weaviate...")
            client.connect()

        question_vector = get_embedding(query)

        collection = client.collections.get("Document")
        result = collection.query.near_vector(
            near_vector=question_vector,
            filters=Filter.by_property("case_id").equal(case_id),
            limit=15  # сначала забираем больше кандидатов
        )

        raw_results = result.objects
        if not raw_results:
            logger.warning(f"⚠️ Нет кандидатов по запросу: '{query}'")
            return []

        # Собираем текстовые кандидаты
        all_chunks = [obj.properties["text"] for obj in raw_results]

        # Пропускаем через reranker
        top_chunks = rerank_chunks(query, all_chunks, top_k=k)

        # Оставляем только те, которые попали в топ
        reranked_matches = [
            obj.properties for obj in raw_results
            if obj.properties["text"] in top_chunks
        ]

        logger.info(f"🔍 После reranking отобрано {len(reranked_matches)} чанков для запроса: '{query}'")
        return reranked_matches

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске чанков: {str(e)}\n{traceback.format_exc()}")
        return []

