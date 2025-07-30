import re
import os
import hashlib
import numpy as np
from numpy.linalg import norm
from app.ml.Embed.embedder import get_embedding  # убедись, что путь корректен

CACHE_DIR = "cache"

def get_cache_path(user_id: int, case_id: int, document_id: int) -> str:
    return os.path.join(CACHE_DIR, str(user_id), str(case_id), f"{document_id}.txt")

def hash_chunk(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()

def is_duplicate_chunk(text: str, user_id: int, case_id: int, document_id: int) -> bool:
    h = hash_chunk(text)
    path = get_cache_path(user_id, case_id, document_id)
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        return h in f.read()

def mark_chunk_as_seen(text: str, user_id: int, case_id: int, document_id: int):
    h = hash_chunk(text)
    path = get_cache_path(user_id, case_id, document_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(h + "\n")

def clear_seen_chunks(user_id: int, case_id: int, document_id: int):
    path = get_cache_path(user_id, case_id, document_id)
    if os.path.exists(path):
        os.remove(path)

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    return float(np.dot(vec1, vec2) / (norm(vec1) * norm(vec2)))

def extract_structure_blocks(text: str) -> list[str]:
    BLOCK_PATTERN = re.compile(r'''
        (?:(?:Статья|Пункт|Раздел|Глава)\s+\d+[а-яА-Я\.\-\d]*) |
        (?:^Протокол\s+от\s+\d{1,2}\.\d{2}\.\d{4}) |
        (?:Постановление\s+от\s+\d{1,2}\.\d{2}\.\d{4}) |
        (?:^[А-ЯЁ][^\n]{0,80}\n)
    ''', re.VERBOSE | re.MULTILINE)

    matches = list(BLOCK_PATTERN.finditer(text))
    blocks = []

    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if len(block) > 50:
            blocks.append(block)
    return blocks

def merge_short_blocks(blocks: list[str], min_length: int = 150) -> list[str]:
    merged = []
    buffer = ""
    for block in blocks:
        if len(block) < min_length:
            buffer += " " + block
        else:
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            merged.append(block)
    if buffer:
        merged.append(buffer.strip())
    return merged

def post_split_cleaning(chunk: str) -> str:
    return re.sub(r'\s+', ' ', chunk.strip())

def smart_chunk_document(
    text: str,
    user_id: int,
    case_id: int,
    document_id: int,
    similarity_threshold: float = 0.98,
    global_dedup: bool = True
) -> list[str]:
    blocks = extract_structure_blocks(text)
    blocks = merge_short_blocks(blocks)
    raw_chunks = [post_split_cleaning(b) for b in blocks if b.strip()]

    seen_texts = set()
    seen_vectors = []
    unique_chunks = []

    for chunk in raw_chunks:
        key = chunk.lower().strip()

        if key in seen_texts:
            print("⏩ Пропущен дубликат текста.")
            continue

        if global_dedup and is_duplicate_chunk(chunk, user_id, case_id, document_id):
            print("⏩ Пропущен глобальный дубликат.")
            continue

        try:
            emb = get_embedding(chunk)
        except Exception as e:
            print(f"⚠️ Ошибка эмбеддинга: {e}")
            continue

        is_similar = any(
            cosine_similarity(emb, existing) > similarity_threshold
            for existing in seen_vectors
        )
        if is_similar:
            print("⏩ Пропущен семантический дубликат.")
            continue

        seen_texts.add(key)
        seen_vectors.append(emb)
        unique_chunks.append(chunk)

        if global_dedup:
            mark_chunk_as_seen(chunk, user_id, case_id, document_id)

    return unique_chunks
