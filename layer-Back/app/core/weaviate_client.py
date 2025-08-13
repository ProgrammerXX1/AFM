# app/core/weaviate_client.py
from __future__ import annotations

import os
import uuid
import atexit
import logging
from typing import Optional, List

from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Configure, Property, DataType, VectorDistances

logger = logging.getLogger(__name__)

_CLIENT: Optional[WeaviateClient] = None

def _str_to_bool(value: str) -> bool:
    return str(value).lower() in ("true", "1", "yes", "y")

def _build_client() -> WeaviateClient:
    return WeaviateClient(
        connection_params=ConnectionParams.from_params(
            http_host=os.getenv("WEAVIATE_HTTP_HOST", "localhost"),
            http_port=int(os.getenv("WEAVIATE_HTTP_PORT", 8080)),
            http_secure=_str_to_bool(os.getenv("WEAVIATE_HTTP_SECURE", "false")),
            grpc_host=os.getenv("WEAVIATE_GRPC_HOST", "localhost"),
            grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", 50051)),
            grpc_secure=_str_to_bool(os.getenv("WEAVIATE_GRPC_SECURE", "false")),
        ),
        additional_config=AdditionalConfig(grpc=True, timeout=Timeout(init=10)),
        skip_init_checks=True,
    )

def get_client() -> WeaviateClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _build_client()
    return _CLIENT

def connect() -> None:
    c = get_client()
    if not c.is_connected():
        logger.info("🔌 Подключение к Weaviate...")
        c.connect()

def is_connected() -> bool:
    try:
        return get_client().is_connected()
    except Exception:
        return False

def close_client() -> None:
    global _CLIENT
    if _CLIENT is None:
        return
    try:
        if _CLIENT.is_connected():
            logger.info("🧹 Закрываем Weaviate-соединение...")
            _CLIENT.close()
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при закрытии Weaviate: {e}")

atexit.register(close_client)

# 🔁 Back-compat shim: старый импорт `from ... import client` будет работать
class _ClientProxy:
    def __getattr__(self, name):
        # авто-коннект при первом обращении
        connect()
        return getattr(get_client(), name)
    def __repr__(self):
        return "<WeaviateClientProxy (lazy)>"

client = _ClientProxy()  # ← добавлено

# также оставим совместимое имя, если где-то вызывается ensure_connection()
def ensure_connection() -> None:  # ← добавлено
    connect()

def ensure_schema() -> None:
    connect()
    try:
        existing = get_client().collections.list_all()
        if "Document" not in existing:
            get_client().collections.create(
                name="Document",
                properties=[
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="text", data_type=DataType.TEXT),
                    Property(name="filetype", data_type=DataType.TEXT),
                    Property(name="case_id", data_type=DataType.INT),
                    Property(name="document_id", data_type=DataType.INT),
                    Property(name="user_id", data_type=DataType.INT),
                    Property(name="chunk_type", data_type=DataType.TEXT),
                    Property(name="chunk_subtype", data_type=DataType.TEXT),
                    Property(name="source_page", data_type=DataType.INT),
                    Property(name="confidence", data_type=DataType.NUMBER),
                    Property(name="hash", data_type=DataType.TEXT),
                ],
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                    vector_length=768,
                ),
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
    vector: List[float],
    document_id: int,
    user_id: int,
    chunk_type: str,
    confidence: float,
    hash: str,
    chunk_subtype: str | None = None,
    source_page: int | None = None,
) -> str:
    connect()
    try:
        doc_uuid = str(uuid.uuid4())
        collection = get_client().collections.get("Document")
        props = {
            "title": title,
            "text": text,
            "filetype": filetype,
            "case_id": case_id,
            "document_id": document_id,
            "user_id": user_id,
            "chunk_type": chunk_type,
            "confidence": confidence,
            "hash": hash,
        }
        if chunk_subtype:
            props["chunk_subtype"] = chunk_subtype
        if source_page is not None:
            props["source_page"] = source_page

        collection.data.insert(uuid=doc_uuid, properties=props, vector=vector)
        logger.info(f"✅ Чанк сохранён в Weaviate: UUID={doc_uuid}")
        return doc_uuid
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении чанка в Weaviate: {str(e)}")
        raise
