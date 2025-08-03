import re
import hashlib
from typing import Dict, List

MIN_LEN = 100

SECTION_TO_TYPE = {
    "Заголовок": "intro",
    "Вводная часть": "intro",
    "Фактическая часть": "facts",
    "Юридическая оценка": "legal",
    "Резолютивная часть": "resolution",
    "Права подозреваемого": "legal_notice",
    "Права и обязанности": "legal_notice",
    "Суть показаний": "testimony",
    "Основные показания": "testimony",
    "Подпись": "signature",
    "Подписи": "signature",
    "Принято следователем": "service_data",
    "Служебные данные": "service_data",
    "Завершение": "signature",
    "Завершение допроса": "signature",
    "Ознакомление": "service_data",
}


def normalize_text(text: str) -> str:
    return ' '.join(text.lower().strip().split())


def _chunk_by_sections(
    text: str,
    sections: Dict[str, str],
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    pattern = re.compile(
        "|".join(f"(?P<{title}>{regex})" for title, regex in sections.items()),
        re.MULTILINE | re.IGNORECASE
    )
    matches = list(pattern.finditer(text))
    chunks = []

    for i, match in enumerate(matches):
        title = match.lastgroup or "Без названия"
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) >= MIN_LEN:
            chunk_type = SECTION_TO_TYPE.get(title, "other")
            chunk_subtype = title.lower().replace(" ", "_")
            chunk_hash = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()
            semantic_hash = hashlib.md5(normalize_text(chunk_text).encode("utf-8")).hexdigest()

            chunks.append({
                "title": title,
                "chunk_type": chunk_type,
                "chunk_subtype": chunk_subtype,
                "text": chunk_text,
                "filetype": filetype,
                "case_id": case_id,
                "document_id": document_id,
                "user_id": user_id,
                "confidence": 1.0,
                "hash": chunk_hash,
                "semantic_hash": semantic_hash,
                "position": i + 1,
                "source_page": -1
            })

    return chunks
