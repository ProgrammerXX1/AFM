import uuid
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
import logging
logger = logging.getLogger(__name__)

# Подключение к Weaviate
client = WeaviateClient(
    connection_params=ConnectionParams.from_params(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False
    ),
    additional_config=AdditionalConfig(
        grpc=True,
        timeout=Timeout(init=10)
    ),
    skip_init_checks=True
)

def ensure_schema():
    """Проверка и создание схемы 'Document' в Weaviate."""
    try:
        if not client.is_connected():
            print("🔌 Подключаемся к Weaviate...")
            client.connect()

        existing = client.collections.list_all()

        if "Document" not in existing:
            client.collections.create(
                name="Document",
                properties=[
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="text", data_type=DataType.TEXT),
                    Property(name="filetype", data_type=DataType.TEXT),
                    Property(name="case_id", data_type=DataType.INT),
                ],
                vectorizer_config=Configure.Vectorizer.none(),  # Отключаем встроенный векторизатор
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE  # Используем объект VectorDistances.COSINE
                )
            )
            print("✅ Коллекция Document создана")
        else:
            print("✅ Коллекция Document уже существует")
    except Exception as e:
        print(f"❌ Ошибка при создании схемы: {str(e)}")
        raise

def save_to_weaviate(title: str, text: str, filetype: str, case_id: int, vector: list[float]) -> str:
    """Сохранение одного чанка в Weaviate."""
    try:
        doc_uuid = str(uuid.uuid4())
        collection = client.collections.get("Document")
        collection.data.insert(
            uuid=doc_uuid,
            properties={
                "title": title,
                "text": text,
                "filetype": filetype,
                "case_id": case_id,
            },
            vector=vector
        )
        print(f"🧾 weaviate_id сохранён: {doc_uuid}")
        return doc_uuid
    except Exception as e:
        print(f"❌ Ошибка при сохранении чанка в Weaviate: {str(e)}")
        raise

def get_documents_by_case(case_id: int, question: str, limit: int = 10) -> list[dict]:
    """Поиск документов по case_id и вопросу с использованием векторного поиска."""
    try:
        from app.ml.embedder import get_embedding
        query_vector = get_embedding(question)

        if not client.is_connected():
            print("🔌 Подключаемся к Weaviate...")
            client.connect()

        collection = client.collections.get("Document")
        result = collection.query.near_vector(
            near_vector=query_vector,
            filters=Configure.Filter.by_property("case_id").equal(case_id),
            limit=limit
        )
        return [obj.properties for obj in result.objects]
    except Exception as e:
        print(f"❌ Ошибка при поиске документов: {str(e)}")
        return []
    
def initialize_weaviate():
    if not client.is_connected():
        logger.info("Connecting to Weaviate...")
        client.connect()
    ensure_schema()