import os
import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

GENERATOR_URL = os.getenv("GENERATOR_URL")
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL")

SYSTEM_PROMPT = (
    "Ты — юридический ассистент в Республике Казахстан. "
    "На основе представленного текста уголовного дела составь официальный документ — "
    "«Постановление о квалификации уголовного правонарушения». "
    "Не выдумывай, не сокращай, используй только факты из текста. "

    "Формат строго такой:\n"
    "1. Блок «СОГЛАСОВЫВАЮ» с должностью и ФИО прокурора (если есть).\n"
    "2. Заголовок: «ПОСТАНОВЛЕНИЕ о квалификации уголовного правонарушения»\n"
    "3. Дата, место, должность и ФИО следователя.\n"
    "4. Раздел «УСТАНОВИЛ» — изложи все факты подробно.\n"
    "5. Раздел «ПОСТАНОВИЛ» — укажи статью УК РК.\n"
    "6. Подпись следователя с датой, если есть.\n"
    "7. QR-блок, если упоминается.\n\n"

    "❗ Не используй шаблоны РФ. Работай только с данными из документа. Не вставляй пустые поля. "
    "Пример: не пиши 'имя и фамилия', а напиши 'Закиев Е.Б.', если это указано. "
    "Если нет данных — не пиши этот блок. "
    "Пиши как реальный юрист. Используй деловой стиль."
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


def generate_investigation_plan(chunks: List[Dict]) -> str:
    try:
        context = build_context(chunks)
        prompt = f"Вот материалы уголовного дела:\n\n{context}\n\nСоставь полноценное постановление о квалификации уголовного правонарушения."

        payload = {
            "model": GENERATOR_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }

        response = requests.post(GENERATOR_URL, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("message", {}).get("content", "").strip()

    except Exception as e:
        logger.exception("Ошибка генерации плана")
        return "❌ Ошибка при генерации плана. Попробуйте позже."
