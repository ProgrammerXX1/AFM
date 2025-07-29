import requests
import os
import logging

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# 🧠 Инструкция для модели (строгая юридическая роль)
SYSTEM_PROMPT = (
    "Ты — юридический ассистент. "
    "Отвечай строго на основе предоставленного контекста. "
    "Если в контексте нет информации для точного ответа — прямо скажи об этом. "
    "Не выдумывай, не додумывай, не используй общие знания вне контекста. "
    "Не предлагай гипотез. Отвечай кратко, формально, как юрист."
)

def generate_answer(prompt: str) -> str:
    """Генерация ответа с использованием Ollama и строгой инструкцией."""
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
            return data["message"]["content"]
        else:
            logger.error(f"Некорректный формат ответа от модели: {data}")
            return "⚠️ Ошибка: модель вернула неожиданный ответ."
    except Exception as e:
        logger.exception("Ошибка при генерации ответа")
        return "❌ Ошибка генерации ответа. Попробуйте позже."
