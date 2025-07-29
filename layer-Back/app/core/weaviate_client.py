import uuid
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
import logging

logger = logging.getLogger(__name__)

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

def ensure_connection():
    """Проверка и установка соединения с Weaviate."""
    if not client.is_connected():
        logger.info("Подключение к Weaviate...")
        client.connect()

def initialize_weaviate():
    """Инициализация подключения к Weaviate и создание схемы."""
    try:
        ensure_connection()
        ensure_schema()
    except Exception as e:
        logger.error(f"Ошибка инициализации Weaviate: {str(e)}")
        raise

def ensure_schema():
    """Проверка и создание схемы 'Document' в Weaviate."""
    try:
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
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                    vector_length=768
                )
            )
            logger.info("Коллекция Document создана")
        else:
            logger.info("Коллекция Document уже существует")
    except Exception as e:
        logger.error(f"Ошибка при создании схемы: {str(e)}")
        raise

def save_to_weaviate(title: str, text: str, filetype: str, case_id: int, vector: list[float]) -> str:
    """Сохранение чанка в Weaviate."""
    try:
        ensure_connection()  # Проверяем подключение перед операцией
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
        logger.info(f"Чанк сохранён с weaviate_id: {doc_uuid}")
        return doc_uuid
    except Exception as e:
        logger.error(f"Ошибка при сохранении чанка в Weaviate: {str(e)}")
        raise

def delete_from_weaviate(weaviate_id: str) -> bool:
    """Удаляет объект по UUID из коллекции Weaviate."""
    try:
        if not client.is_connected():
            logger.info("🔌 Подключаемся к Weaviate...")
            client.connect()

        collection = client.collections.get("Document")
        collection.data.delete_by_id(weaviate_id)
        logger.info(f"🗑️ Удалён объект с weaviate_id={weaviate_id}")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Ошибка удаления из Weaviate: {str(e)}")
        return False