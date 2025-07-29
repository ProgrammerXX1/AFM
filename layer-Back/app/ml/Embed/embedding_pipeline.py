import logging
import traceback

from app.core.weaviate_client import save_to_weaviate, client
from app.ml.Embed.embedder import get_embedding
from app.ml.Embed.chunker import smart_chunk_document  # ← твой умный чанкер
from weaviate.classes.query import Filter

logger = logging.getLogger(__name__)

def index_full_document(title: str, text: str, filetype: str, case_id: int, document_id: int | None = None):
    """Индексация документа с разбиением на смысловые чанки и сохранением в Weaviate."""
    try:
        chunks = smart_chunk_document(text)
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
    """Поиск релевантных чанков по вопросу и делу (case_id)."""
    try:
        if not client.is_connected():
            logger.info("🔌 Подключаемся к Weaviate...")
            client.connect()

        question_vector = get_embedding(query)

        collection = client.collections.get("Document")
        result = collection.query.near_vector(
            near_vector=question_vector,
            filters=Filter.by_property("case_id").equal(case_id),
            limit=k
        )

        matches = [obj.properties for obj in result.objects]
        logger.info(f"🔍 Найдено {len(matches)} совпадений по вопросу: '{query}'")
        return matches

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске чанков: {str(e)}\n{traceback.format_exc()}")
        return []
