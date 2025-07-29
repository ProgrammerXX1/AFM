from app.ml.chunker import split_text_to_chunks
from app.ml.embedder import get_embedding
from app.core.weaviate_client import save_to_weaviate, client
import logging
from weaviate.classes.query import Filter
logger = logging.getLogger(__name__)
import traceback

def index_full_document(title: str, text: str, filetype: str, case_id: int):
    """Индексация документа с разбиением на чанки."""
    try:
        chunks = split_text_to_chunks(text)
        logger.info(f"Разбито на {len(chunks)} чанков для файла {title}")

        for i, chunk in enumerate(chunks):
            try:
                vector = get_embedding(chunk)
                if vector is None:
                    logger.warning(f"❗Embedding для чанка {i+1} — None. Пропущено.")
                    continue

                save_to_weaviate(
                    title=f"{title}_chunk_{i+1}",
                    text=chunk,
                    filetype=filetype,
                    case_id=case_id,
                    vector=vector
                )
            except Exception as e:
                logger.error(
                    f"❌ Ошибка при индексации чанка {i+1} файла {title}: {str(e)}\n{traceback.format_exc()}"
                )
                continue

    except Exception as e:
        logger.error(
            f"❌ Ошибка при разбиении или индексации документа {title}: {str(e)}\n{traceback.format_exc()}"
        )
        raise


def search_similar_chunks(query: str, case_id: int, k: int = 5):
    """Поиск похожих чанков по вопросу и case_id."""
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
        logger.info(f"🔍 Найдено {len(matches)} совпадений")
        return matches

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске чанков: {str(e)}")
        return []