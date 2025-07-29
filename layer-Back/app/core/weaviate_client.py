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

def save_to_weaviate(title: str, text: str, filetype: str, case_id: int, vector: list[float], document_id: int | None = None) -> str:
    """Сохранение чанка в Weaviate."""
    try:
        ensure_connection()  # Проверяем подключение перед операцией
        doc_uuid = str(uuid.uuid4())
        collection = client.collections.get("Document")

        properties = {
            "title": title,
            "text": text,
            "filetype": filetype,
            "case_id": case_id,
            "document_id": document_id  
        }

        # 💡 Добавляем связь с документом
        if document_id is not None:
            properties["document_id"] = document_id

        collection.data.insert(
            uuid=doc_uuid,
            properties=properties,
            vector=vector
        )

        logger.info(f"Чанк сохранён с weaviate_id: {doc_uuid}")
        return doc_uuid

    except Exception as e:
        logger.error(f"Ошибка при сохранении чанка в Weaviate: {str(e)}")
        raise

def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except:
        return False

def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(DocumentModel).join(CaseModel).filter(
        DocumentModel.id == document_id,
        CaseModel.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # ✅ Удаление всех чанков из Weaviate по document_id
    try:
        if not client.is_connected():
            client.connect()

        collection = client.collections.get("Document")

        # ❗Правильный способ сформировать where-фильтр для v4
        where_filter = Filter.by_property("document_id").equal(document.id)

        delete_result = collection.data.delete_many(where=where_filter)
        logger.info(f"🗑️ Удалено чанков Weaviate: {delete_result['matches']}")

    except Exception as e:
        logger.warning(f"⚠️ Ошибка удаления чанков из Weaviate: {e}")

    db.delete(document)
    db.commit()
    return {"message": "Документ и чанки удалены"}
