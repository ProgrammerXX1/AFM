from typing import List, Dict
from .utils import _chunk_by_sections, normalize_text
import hashlib

def chunk_dopros(
    text: str,
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    sections = {
        "identity_info": r"^Фамилия.*?:.*?$",
        "rights_notice": r"^Права.*?обязанности.*?$",
        "facts": r"^По существу.*?$",
        "conclusion": r"^На этом допрос окончен.*?$",
        "metadata": r"^Следователь.*?$|^Документ подготовил.*?$",
    }
    return _chunk_by_sections(text, sections, filetype, document_id, case_id, user_id)


def post_process_chunks(chunks: List[Dict]) -> List[Dict]:
    """Постобработка чанков допроса: фильтрация, уникальность, назначение позиции."""
    processed = []
    seen_hashes = set()
    position = 1

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if len(text) < 100:
            continue

        chunk_hash = chunk.get("hash") or hashlib.md5(text.encode("utf-8")).hexdigest()
        if chunk_hash in seen_hashes:
            continue
        seen_hashes.add(chunk_hash)

        semantic_hash = chunk.get("semantic_hash") or hashlib.md5(normalize_text(text).encode("utf-8")).hexdigest()
        chunk["hash"] = chunk_hash
        chunk["semantic_hash"] = semantic_hash
        chunk["position"] = position
        chunk["source_page"] = chunk.get("source_page", -1)

        processed.append(chunk)
        position += 1

    return processed
