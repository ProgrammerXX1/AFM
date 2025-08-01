from app.ml.Embed.pipeline import search_similar_chunks
from app.ml.Generation.generator import generate_answer
import logging

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 4000

def truncate_context(text: str, limit: int = MAX_CONTEXT_CHARS) -> str:
    return text[:limit] + "..." if len(text) > limit else text

def answer_query(case_id: int, question: str) -> str:
    """Генерация ответа на вопрос на основе контекста из документов."""
    try:
        docs = search_similar_chunks(question, case_id, k=10)
        if not docs:
            return "❗Контекст не найден. Уточните вопрос или загрузите документы."

        context_parts = []
        for doc in docs:
            try:
                text = doc.get("text", "")
                if text:
                    context_parts.append(text)
                else:
                    logger.warning("Чанк без текста: %s", doc)
            except Exception as e:
                logger.warning(f"Пропущен документ: {e}")

        if not context_parts:
            return "❗В документах не найден текст для анализа."

        context = "\n\n".join(context_parts)
        context = truncate_context(context)

        prompt = f"Вопрос: {question}\nКонтекст:\n{context}\nОтвет:"
        return generate_answer(prompt)

    except Exception as e:
        logger.exception("Ошибка в answer_query")
        return "❌ Не удалось сгенерировать ответ. Попробуйте позже."
