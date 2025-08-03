import uuid
from app.security.security import User, get_current_user
from app.models.cases import DocumentModel, CaseModel
from app.db.database import get_db
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
import logging
from weaviate.classes.query import Filter
from fastapi import HTTPException, Depends, Query
from sqlalchemy.orm import Session
import os
logger = logging.getLogger(__name__)

def str_to_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")

client = WeaviateClient(
    connection_params=ConnectionParams.from_params(
        http_host=os.getenv("WEAVIATE_HTTP_HOST", "localhost"),
        http_port=int(os.getenv("WEAVIATE_HTTP_PORT", 8080)),
        http_secure=str_to_bool(os.getenv("WEAVIATE_HTTP_SECURE", "false")),
        grpc_host=os.getenv("WEAVIATE_GRPC_HOST", "localhost"),
        grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", 50051)),
        grpc_secure=str_to_bool(os.getenv("WEAVIATE_GRPC_SECURE", "false")),
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
                    Property(name="document_id", data_type=DataType.INT),
                    Property(name="user_id", data_type=DataType.INT),
                    Property(name="chunk_type", data_type=DataType.TEXT),
                    Property(name="chunk_subtype", data_type=DataType.TEXT),   # ✅ добавлено
                    Property(name="source_page", data_type=DataType.INT),      # ✅ добавлено
                    Property(name="confidence", data_type=DataType.NUMBER),
                    Property(name="hash", data_type=DataType.TEXT),
                ],
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                    vector_length=768
                )
            )
            logger.info("✅ Коллекция Document создана")
        else:
            logger.info("ℹ️ Коллекция Document уже существует")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании схемы: {str(e)}")
        raise
def save_to_weaviate(
    title: str,
    text: str,
    filetype: str,
    case_id: int,
    vector: list[float],
    document_id: int,
    user_id: int,
    chunk_type: str,
    confidence: float,
    hash: str,
    chunk_subtype: str = None,   # ✅ опционально
    source_page: int = None      # ✅ опционально
) -> str:
    """Сохранение чанка в Weaviate с расширенными метаданными."""
    try:
        ensure_connection()
        doc_uuid = str(uuid.uuid4())
        collection = client.collections.get("Document")

        properties = {
            "title": title,
            "text": text,
            "filetype": filetype,
            "case_id": case_id,
            "document_id": document_id,
            "user_id": user_id,
            "chunk_type": chunk_type,
            "confidence": confidence,
            "hash": hash
        }

        if chunk_subtype:
            properties["chunk_subtype"] = chunk_subtype
        if source_page is not None:
            properties["source_page"] = source_page

        collection.data.insert(
            uuid=doc_uuid,
            properties=properties,
            vector=vector
        )

        logger.info(f"✅ Чанк сохранён в Weaviate: UUID={doc_uuid}")
        return doc_uuid

    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении чанка в Weaviate: {str(e)}")
        raise


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except:
        return False

