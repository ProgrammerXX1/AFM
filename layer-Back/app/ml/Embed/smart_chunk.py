from typing import List
from app.ml.Embed.chunker.base import chunk_by_filetype, get_postprocessor, detect_doc_type

def smart_chunk_document(
    text: str,
    case_id: int,
    document_id: int,
    doc_type: str = "auto",
    min_len: int = 100,
    user_id: int = 1
) -> List[dict]:
    """Чанкирование через base.py с удалением дублей и постобработкой."""

    # детектим тип
    doc_type_final = detect_doc_type(text) if doc_type == "auto" else doc_type.lower()

    # чанкируем
    raw_chunks = chunk_by_filetype(
        text=text,
        filetype=doc_type,
        document_id=document_id,
        case_id=case_id,
        user_id=user_id
    )

    # фильтрация дубликатов
    seen = set()
    filtered = []
    for chunk in raw_chunks:
        norm = chunk["text"].strip()
        if len(norm) < min_len or norm in seen:
            continue
        seen.add(norm)
        chunk.setdefault("chunk_subtype", None)
        chunk.setdefault("source_page", -1)
        filtered.append(chunk)

    print(f"📦 До удаления дубликатов: {len(raw_chunks)} → после: {len(filtered)}")

    # постобработка
    post_process = get_postprocessor(doc_type_final)
    final_chunks = post_process(filtered)
    print(f"✅ После постобработки: {len(final_chunks)} чанков")

    return final_chunks
