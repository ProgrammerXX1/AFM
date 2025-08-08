import json
import hashlib
import os
import time
import requests

from app.core.weaviate_client import client

# === Конфигурация ===
EMBEDDER_URL = os.getenv("EMBEDDER_URL", "https://35966ecd792c.ngrok-free.app/api/embeddings")
EMBEDDER_MODEL = os.getenv("EMBEDDER_MODEL", "nomic-embed-text")
JSON_PATH = "app/utils/parsers/full_codex.json"
COLLECTION_NAME = "Norm"
EMBEDDING_TIMEOUT = 10
UPLOAD_DELAY = 0.2  # между вставками

# === Подключение к Weaviate ===
if not client.is_connected():
    client.connect()
collection = client.collections.get(COLLECTION_NAME)

# === Функции ===
def compute_hash(text: str) -> str:
    return hashlib.md5(text.strip().encode()).hexdigest()

def get_embedding_safe(text: str):
    """Надёжная функция получения embedding — будет повторять до успеха."""
    while True:
        try:
            response = requests.post(
                EMBEDDER_URL,
                json={"model": EMBEDDER_MODEL, "prompt": text, "stream": False},
                timeout=EMBEDDING_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"] if "embedding" in data else data[0]["embedding"]
        except Exception as e:
            print(f"❗ Ошибка запроса embedding: {e} — повтор через 3 сек...")
            time.sleep(3)

# === Загрузка JSON ===
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# === Загрузка в Weaviate ===
for i, item in enumerate(data):
    success = False
    while not success:
        try:
            hash_ = compute_hash(item["text"])
            vector = get_embedding_safe(item["text"])  # 🔁 гарантированно вернёт embedding

            collection.data.insert(
                properties={
                    "article": item.get("article"),
                    "title": item.get("title"),
                    "text": item.get("text"),
                    "chapter": item.get("chapter"),
                    "section": item.get("section"),
                    "tags": item.get("tags"),
                    "hash": hash_,
                },
                vector=vector
            )

            print(f"✅ [{i+1}/{len(data)}] Статья {item.get('article')} загружена.")
            time.sleep(UPLOAD_DELAY)
            success = True

        except Exception as e:
            print(f"❌ [{i+1}] Ошибка при загрузке статьи {item.get('article')}: {e}")
            print("🔁 Повторная попытка через 3 сек...")
            time.sleep(3)
