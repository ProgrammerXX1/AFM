import requests
import os
import logging

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# 🧠 Усиленная инструкция для модели (юридическая строгость)
SYSTEM_PROMPT = (
    "Ты выступаешь в роли профессионального юридического консультанта. "
    "Твоя задача — давать точные, однозначные и строго обоснованные ответы "
    "исключительно на основе предоставленного контекста.\n\n"
    "⚠️ Запрещено:\n"
    "- Делать предположения или догадки\n"
    "- Использовать знания вне представленного контекста\n"
    "- Излагать информацию неформально или в разговорной форме\n\n"
    "✅ Требуется:\n"
    "- Давать краткий, строгий и формальный ответ\n"
    "- Ссылаться на пункты, статьи, даты, если они есть в контексте\n"
    "- Если ответа в контексте нет — прямо сообщить: «Информация отсутствует в контексте.»\n"
)

def generate_answer(prompt: str) -> str:
    """Генерация ответа с использованием Ollama и строгой юридической инструкцией."""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
        }
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

        data = response.json()
        if "message" in data and "content" in data["message"]:
            return data["message"]["content"].strip()
        else:
            logger.error(f"Некорректный формат ответа от модели: {data}")
            return "⚠️ Ошибка: модель вернула неожиданный ответ."
    except Exception as e:
        logger.exception("Ошибка при генерации ответа")
        return "❌ Ошибка генерации ответа. Попробуйте позже."
