import re
from app.ml.Embed.embedder import get_embedding
import numpy as np


def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def extract_structure_blocks(text: str) -> list[str]:
    """Разделение текста на логические блоки по юр. структуре: статьи, пункты, заголовки."""
    BLOCK_PATTERN = re.compile(r'''
        (?:(?:Статья|Пункт|Раздел|Глава)\s+\d+[а-яА-Я\.\-\d]*) |
        (?:^Протокол\s+от\s+\d{1,2}\.\d{2}\.\d{4}) |
        (?:Постановление\s+от\s+\d{1,2}\.\d{2}\.\d{4}) |
        (?:^[А-ЯЁ][^\n]{0,80}\n)  # заголовки
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


def merge_short_blocks(blocks: list[str], min_length: int = 300) -> list[str]:
    """Объединение коротких чанков с предыдущими или следующими."""
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
    """Очистка чанка от лишних переносов и пробелов."""
    chunk = chunk.strip()
    chunk = re.sub(r'\s+', ' ', chunk)
    return chunk


def smart_chunk_document(text: str, similarity_threshold: float = 0.95) -> list[str]:
    """Умное чанкирование с удалением дубликатов по тексту и по смыслу (эмбеддингу)."""
    blocks = extract_structure_blocks(text)
    blocks = merge_short_blocks(blocks)
    raw_chunks = [post_split_cleaning(b) for b in blocks if b.strip()]

    seen_texts = set()
    seen_vectors = []
    unique_chunks = []

    for chunk in raw_chunks:
        key = chunk.lower().strip()
        
        # 1. Фильтрация по тексту
        if key in seen_texts:
            print(f"⏩ Пропущен дубликат текста.")
            continue

        # 2. Семантическая фильтрация
        try:
            emb = get_embedding(chunk)
        except Exception as e:
            print(f"⚠️ Проблема с эмбеддингом: {e}")
            continue

        is_similar = False
        for existing_emb in seen_vectors:
            if cosine_similarity(emb, existing_emb) > similarity_threshold:
                is_similar = True
                print(f"⏩ Пропущен семантический дубликат.")
                break

        if is_similar:
            continue

        seen_texts.add(key)
        seen_vectors.append(emb)
        unique_chunks.append(chunk)

    return unique_chunks