import requests
import os
import logging

logger = logging.getLogger(__name__)

EMBEDDER_URL = os.getenv("EMBEDDER_URL")
EMBEDDER_MODEL = os.getenv("EMBEDDER_MODEL")

def get_embedding(text: str) -> list[float]:
    """Получение эмбеддинга для текста через Ollama."""
    try:
        if not text or not text.strip():
            raise ValueError("Пустой текст для эмбеддинга.")

        logger.debug(f"📎 Эмбеддинг для текста (длина {len(text)}): {text[:60]}...")

        response = requests.post(
            f"{EMBEDDER_URL}/api/embeddings",
            json={"model": EMBEDDER_MODEL, "prompt": text}
        )
        response.raise_for_status()
        data = response.json()
        embedding = data.get("embedding")

        # Обработка вложенного массива
        if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
            embedding = embedding[0]

        if not isinstance(embedding, list) or not embedding:
            raise ValueError("Некорректный формат embedding: None или пустой")

        return [float(x) for x in embedding]

    except Exception as e:
        logger.error(f"❌ Ошибка получения эмбеддинга: {str(e)}")
        raise
