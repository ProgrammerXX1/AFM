from typing import List
from app.ml.Embed.chunker.base import chunk_by_filetype

def smart_chunk_document(
    text: str,
    case_id: int,
    document_id: int,
    doc_type: str = "auto",
    min_len: int = 100,
    user_id: int = 1
) -> List[dict]:
    """Чанкирование через router с удалением дублей."""
    raw_chunks = chunk_by_filetype(
        text=text,
        filetype=doc_type,
        document_id=document_id,
        case_id=case_id,
        user_id=user_id
    )

    seen = set()
    result = []

    for chunk in raw_chunks:
        norm_text = chunk["text"].strip()
        if len(norm_text) < min_len or norm_text in seen:
            continue
        seen.add(norm_text)
        result.append(chunk)

    print(f"📦 Чанков до удаления дубликатов: {len(raw_chunks)} → после: {len(result)}")
    return result
