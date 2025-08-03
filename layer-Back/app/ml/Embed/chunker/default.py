import hashlib
import re
from typing import Dict, List
from .utils import normalize_text
from app.ml.Embed.chunker.postprocess import generic_post_process_chunks
MIN_LEN = 100

SECTIONS = {
    "Заголовок": r"^постановление\b.*?$",
    "Фактическая часть": r"^установил:.*?$",
    "Резолютивная часть": r"^постановил:.*?$",
    "Права и обязанности": r"^в\s+соответствии\s+со\s+ст\.ст?\..*?упк\s+рк.*?$",
    "Подписи": r"^(постановление объявил|копию постановления|права разъяснил|следователь|потерпевший).*?$",
    "metadata": r"(qr-код|эцп|mailto:|единый\s+реестр)"
}


def chunk_common(
    text: str,
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    chunks = []
    pattern = re.compile("|".join(f"(?P<{k}>{v})" for k, v in SECTIONS.items()), re.MULTILINE | re.IGNORECASE)
    matches = list(pattern.finditer(text))

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < MIN_LEN:
            continue

        chunk_type = match.lastgroup
        chunk_subtype = chunk_type if chunk_type else "unspecified"
        chunk_hash = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()
        semantic_hash = hashlib.md5(normalize_text(chunk_text).encode("utf-8")).hexdigest()

        chunks.append({
            "title": f"{filetype.capitalize()}_chunk_{idx + 1}",
            "chunk_type": chunk_type or "other",
            "chunk_subtype": chunk_subtype,
            "text": chunk_text,
            "filetype": filetype,
            "case_id": case_id,
            "document_id": document_id,
            "user_id": user_id,
            "confidence": 0.95 if chunk_type != "other" else 0.5,
            "hash": chunk_hash,
            "semantic_hash": semantic_hash,
            "position": idx + 1,
            "source_page": -1
        })

    return chunks

def post_process_chunks(chunks: List[Dict]) -> List[Dict]:
    """Универсальная постобработка: фильтрация, уникальность, позиция, дедупликация по смыслу."""
    seen_hashes = set()
    enriched = []
    position = 1

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if len(text) < MIN_LEN:
            continue

        chunk_hash = chunk.get("hash") or hashlib.md5(text.encode("utf-8")).hexdigest()
        if chunk_hash in seen_hashes:
            continue

        seen_hashes.add(chunk_hash)

        chunk["hash"] = chunk_hash
        chunk["semantic_hash"] = hashlib.md5(normalize_text(text).encode("utf-8")).hexdigest()
        chunk["position"] = position
        chunk["source_page"] = chunk.get("source_page", -1)
        chunk["confidence"] = 1.0

        enriched.append(chunk)
        position += 1

    # ✅ Финальная дедупликация и фильтрация по смыслу
    return generic_post_process_chunks(enriched)