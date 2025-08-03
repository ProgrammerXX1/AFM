import os
import logging
import traceback
import hashlib

from app.core.weaviate_client import save_to_weaviate, client
from app.ml.Embed.smart_chunk import smart_chunk_document
from app.ml.Embed.embedder import get_embedding
from weaviate.classes.query import Filter
from app.ml.Embed.reranker import rerank_chunks

logger = logging.getLogger(__name__)

def clear_seen_chunks(user_id: int, case_id: int, document_id: int, hashes_to_remove: list[str] = None):
    file_path = f"cache/chunks/{user_id}/{case_id}.txt"

    if not os.path.exists(file_path):
        logger.warning(f"⚠️ Файл TXT не найден: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    removed = 0

    for line in lines:
        parts = line.strip().split("|")
        if len(parts) < 4:
            new_lines.append(line)
            continue

        chunk_hash = parts[0]
        try:
            doc_id_in_line = int(parts[3])
        except ValueError:
            new_lines.append(line)
            continue

        # Удаляем:
        # - либо все по document_id (если hashes_to_remove не задан),
        # - либо только совпадающие по hash + document_id
        if doc_id_in_line == document_id and (hashes_to_remove is None or chunk_hash in hashes_to_remove):
            removed += 1
        else:
            new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    logger.info(f"🧹 Удалено {removed} строк из TXT по document_id={document_id}")


def get_hash_path(user_id: int, case_id: int) -> str:
    path = f"cache/chunks/{user_id}/{case_id}.txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def hash_chunk(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

def load_known_hashes(user_id: int, case_id: int) -> set:
    path = get_hash_path(user_id, case_id)
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_hash(user_id: int, case_id: int, chunk_hash: str):
    path = get_hash_path(user_id, case_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{chunk_hash}\n")


import os
import logging
import traceback
import hashlib

from app.core.weaviate_client import save_to_weaviate, client
from app.ml.Embed.smart_chunk import smart_chunk_document
from app.ml.Embed.embedder import get_embedding
from weaviate.classes.query import Filter
from app.ml.Embed.reranker import rerank_chunks

logger = logging.getLogger(__name__)

def get_hash_path(user_id: int, case_id: int) -> str:
    path = f"cache/chunks/{user_id}/{case_id}.txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def load_known_hashes(user_id: int, case_id: int) -> set:
    path = get_hash_path(user_id, case_id)
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_hash(user_id: int, case_id: int, chunk_hash: str):
    path = get_hash_path(user_id, case_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{chunk_hash}\n")

def hash_chunk(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

def index_full_document(
    title: str,
    text: str,
    filetype: str,
    user_id: int,
    case_id: int,
    document_id: int,
    doc_type: str
):
    try:
        chunks = smart_chunk_document(
            text=text,
            case_id=case_id,
            document_id=document_id,
            doc_type=doc_type,
            user_id=user_id
        )

        logger.info(f"📄 Документ '{title}' разбит на {len(chunks)} чанков (до фильтрации).")

        known_hashes = load_known_hashes(user_id, case_id)
        saved_count = 0

        for i, chunk in enumerate(chunks):
            chunk_text = chunk["text"].strip()
            if not chunk_text:
                logger.warning(f"⚠️ Пропущен пустой текст у чанка {i + 1}")
                continue

            chunk_hash = hash_chunk(chunk_text)
            if chunk_hash != chunk["hash"]:
                logger.warning(f"⚠️ Хэш отличается для чанка {i + 1}: recalculated={chunk_hash}, saved={chunk['hash']}")

            if chunk_hash in known_hashes:
                logger.warning(f"⚠️ Пропущен дубликат чанка {i + 1}")
                continue

            vector = get_embedding(chunk_text)
            if not vector:
                logger.warning(f"⚠️ Пропущен пустой эмбеддинг для чанка {i + 1}")
                continue

            save_to_weaviate(
                title=f"{title}_chunk_{i + 1}",
                text=chunk_text,
                filetype=filetype,
                case_id=case_id,
                document_id=document_id,
                user_id=user_id,
                chunk_type=chunk.get("chunk_type", "unknown"),
                chunk_subtype=chunk.get("chunk_subtype", ""),           # ✅ добавлено
                source_page=chunk.get("source_page", -1),               # ✅ добавлено
                confidence=chunk.get("confidence", 0.5),
                hash=chunk_hash,
                vector=vector
            )

            save_hash(user_id, case_id, chunk_hash)
            saved_count += 1

        if len(chunks) == 0:
            logger.warning(f"⚠️ Нет чанков для документа '{title}'.")
        else:
            logger.info(f"✅ Сохранено {saved_count}/{len(chunks)} чанков ({(saved_count/len(chunks))*100:.1f}%) для документа '{title}'")


    except Exception as e:
        logger.error(f"❌ Ошибка индексации документа '{title}': {str(e)}\n{traceback.format_exc()}")
        raise

def search_similar_chunks(query: str, case_id: int, k: int = 5) -> list[dict]:
    """
    Поиск по Weaviate + reranking.
    """
    try:
        if not client.is_connected():
            logger.info("🔌 Подключаемся к Weaviate...")
            client.connect()

        question_vector = get_embedding(query)
        collection = client.collections.get("Document")

        result = collection.query.near_vector(
            near_vector=question_vector,
            filters=Filter.by_property("case_id").equal(case_id),
            limit=15
        )

        raw_results = result.objects
        if not raw_results:
            logger.warning(f"⚠️ Нет кандидатов по запросу: '{query}'")
            return []

        text_to_obj = {}
        for obj in raw_results:
            text = obj.properties.get("text")
            if text and text not in text_to_obj:
                text_to_obj[text] = obj.properties

        unique_texts = list(text_to_obj.keys())
        top_chunks = rerank_chunks(query, unique_texts, top_k=k)
        reranked_matches = [text_to_obj[text] for text in top_chunks if text in text_to_obj]

        logger.info(f"🔍 После reranking отобрано {len(reranked_matches)} чанков для запроса: '{query}'")
        return reranked_matches

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске чанков: {str(e)}\n{traceback.format_exc()}")
        return []
