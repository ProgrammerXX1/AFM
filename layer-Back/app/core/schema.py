import weaviate
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Property, DataType

# Подключение
client = WeaviateClient(
    connection_params=ConnectionParams.from_params(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False
    ),
    additional_config=AdditionalConfig(grpc=True, timeout=Timeout(init=10)),
    skip_init_checks=True
)

try:
    client.connect()

    # Удаление, если коллекция уже существует
    if client.collections.exists("Document"):
        client.collections.delete("Document")
        print("🧹 Старая коллекция 'Document' удалена.")

    # Создание конфигурации коллекции без встроенного векторизатора
    collection_config = {
    "name": "Document",
    "properties": [
        Property(name="title", data_type=DataType.TEXT),
        Property(name="text", data_type=DataType.TEXT),
        Property(name="filetype", data_type=DataType.TEXT),
        Property(name="chunk_type", data_type=DataType.TEXT),
        Property(name="chunk_subtype", data_type=DataType.TEXT),   # ✅ добавлено
        Property(name="confidence", data_type=DataType.NUMBER),
        Property(name="hash", data_type=DataType.TEXT),
        Property(name="source_page", data_type=DataType.INT),      # ✅ добавлено
        Property(name="case_id", data_type=DataType.INT),
        Property(name="document_id", data_type=DataType.INT),
        Property(name="user_id", data_type=DataType.INT),
    ]


        # Не указываем vectorizer, чтобы использовать внешние эмбеддинги
        # Параметры индекса (HNSW, cosine) используются по умолчанию
    }

    # Создание коллекции с распаковкой конфигурации
    client.collections.create(**collection_config)
    print("✅ Коллекция 'Document' создана.")

except Exception as e:
    print(f"Ошибка: {e}")
finally:
    client.close()
    print("🔌 Соединение закрыто.")