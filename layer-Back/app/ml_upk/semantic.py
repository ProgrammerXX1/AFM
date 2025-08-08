import os
import requests
from app.core.weaviate_client import client
from weaviate.classes.query import HybridFusion
EMBEDDER_URL = os.getenv("EMBEDDER_URL", "https://35966ecd792c.ngrok-free.app/api/embeddings")
EMBEDDER_MODEL = os.getenv("EMBEDDER_MODEL", "nomic-embed-text")
COLLECTION_NAME = "Norm"

# ✅ Подключение к Weaviate
if not client.is_connected():
    client.connect()
collection = client.collections.get(COLLECTION_NAME)

# ✅ Получить эмбеддинг запроса
def get_query_embedding(query: str):
    response = requests.post(
        EMBEDDER_URL,
        json={"model": EMBEDDER_MODEL, "prompt": query, "stream": False},
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
    return data["embedding"] if "embedding" in data else data[0]["embedding"]

# ✅ Векторный поиск (Weaviate SDK v4)
from weaviate.classes.query import Filter

def search_law(query: str, top_k: int = 5, chapter: str = None):
    # 1. Получаем embedding
    vector = get_query_embedding(query)

    # 2. (Необязательно) фильтр по главе
    filters = None
    if chapter:
        filters = Filter.by_property("chapter").equal(chapter)

    # 3. Запрос в Weaviate
    results = collection.query.hybrid(
        query=query,
        alpha=0.5,  # 0.0 = только BM25, 1.0 = только vector, по умолч. 0.5
        vector=vector,
        filters=filters,
        limit=top_k
    ).objects

    # 4. Вывод
    for obj in results:
        props = obj.properties
        print(f"\n📘 Статья {props.get('article')} — {props.get('chapter')}")
        print(f"📌 Текст: {props.get('text')[:500]}...\n")

search_law("Глава 2. Задачи и принципы уголовного процесса")
