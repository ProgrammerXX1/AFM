# app/ml/embedder.py

import requests
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3")  # или bge-base, nomic-embed, что ты используешь

def get_embedding(text: str) -> list[float]:
    print(f"🔍 Получаем эмбеддинг для текста (длина {len(text)}): {text[:60]}...")
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": MODEL_NAME, "prompt": text}
    )
    response.raise_for_status()

    embedding = response.json().get("embedding")
    
    # Исправляем, если вложен: [[...]] → [...]
    if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
        embedding = embedding[0]

    if not isinstance(embedding, list) or not embedding:
        raise ValueError("❌ Некорректный embedding")
    # Приводим к list[float] на всякий случай
    return [float(x) for x in embedding]
