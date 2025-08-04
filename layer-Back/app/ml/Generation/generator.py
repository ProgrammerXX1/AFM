import os
import requests
import logging
from typing import List, Dict
from app.ml.Generation.retriever import hybrid_search

logger = logging.getLogger(__name__)

GENERATOR_URL = os.getenv("GENERATOR_URL")
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL")

SYSTEM_PROMPT = (
    "Ты — юридический ассистент в Республике Казахстан. Всегда отвечай на русском языке.Отвечай от своего имени. "
    "На основе текста уголовного дела составь официальный документ — "
    "«Постановление о квалификации деяния подозреваемого». "
    "Пиши строго как действующий следователь, с соблюдением делового, официально-юридического стиля. "
    "Используй реальные шаблоны уголовного процессуального оформления. "
    "Не используй сокращений и не выдумывай фактов — работай только с представленным текстом.\n\n"

    "Формат:\n"
    "1. Заголовок: «ПОСТАНОВЛЕНИЕ о квалификации деяния подозреваемого»\n"
    "2. Дата, город, должность и ФИО следователя\n"
    "3. Раздел «УСТАНОВИЛ» — подробное описание фактов и обстоятельств\n"
    "4. Раздел «ПОСТАНОВИЛ» — указание деяний(ей)\n"
    "5. Подпись следователя с должностью, ФИО, и возможный QR-код, если он есть\n\n"

    "Если какой-то блок отсутствует в исходном тексте — не выдумывай его и не вставляй заглушки. "
    "Оформляй как готовый официальный процессуальный документ. "
    "Соблюдай структуру и стиль, как в реальных постановлениях из ИС «Единый реестр досудебных расследований»."
)


def build_context(chunks: List[Dict]) -> str:
    result = []
    for chunk in chunks:
        if isinstance(chunk, dict) and "text" in chunk:
            title = chunk.get("title", "Фрагмент")
            chunk_type = chunk.get("chunk_type", "unknown")
            text = chunk["text"].strip()
            if text:
                result.append(f"{title} ({chunk_type}):\n{text}")
    return "\n\n".join(result)


def generate_investigation_plan(case_id: int) -> str:
    try:
        query = "Составь постановление о квалификации уголовного правонарушения"
        chunks = hybrid_search(case_id=case_id, query=query, top_k=5)

        if not chunks:
            logger.warning("❗ Не найдено чанков по делу")
            return "Нет данных для генерации постановления."

        logger.info(f"🔍 Найдено {len(chunks)} релевантных чанков")
        for i, ch in enumerate(chunks):
            logger.debug(f"Chunk {i+1}: [{ch.get('chunk_type')}] {ch.get('text', '')[:400]}...")

        context = build_context(chunks)

        full_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Вот материалы уголовного дела:\n\n{context}\n\n"
            f"Составь полноценное постановление о квалификации уголовного правонарушения на русском."
        )

        payload = {
            "model": GENERATOR_MODEL,
            "prompt": full_prompt,
            "stream": False
        }

        logger.debug(f"📤 Отправка запроса в Ollama ({GENERATOR_URL}): {GENERATOR_MODEL}")
        response = requests.post(GENERATOR_URL, json=payload)
        response.raise_for_status()

        result = response.json()
        return result.get("response", "").strip()

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка запроса к модели: {e}")
        return "⚠️ Ошибка связи с моделью генерации."

    except Exception as e:
        logger.exception("Ошибка генерации постановления")
        return "❌ Ошибка при генерации постановления. Попробуйте позже."
