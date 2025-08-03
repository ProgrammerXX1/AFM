import re
import hashlib
from typing import List, Dict

MIN_LEN = 100

SECTION_TITLES = [
    "recipient",
    "applicant_info",
    "title",
    "body",
    "signature",
    "service_data",
    "metadata",
]

SECTION_TO_TYPE = {
    "recipient": "intro",
    "applicant_info": "applicant_info",
    "title": "title",
    "body": "body",
    "signature": "signature",
    "service_data": "receipt",
    "metadata": "metadata"
}


SECTION_PATTERNS = {
    "recipient": r"^следователю\s+(по\s+особо\s+важным\s+делам\s+)?следственного\s+управления[^\n]{0,100}",
    "applicant_info": r"(г\.р\.|проживающ(ая|ий)|[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.)",
    "title": r"\bзаявление\b",
    "body": r"^от\s+ознакомления.*|^(об|я)\s+[^\n]{5,}",
    "signature": r"^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.\s*\n\d{2}\.\d{2}\.\d{4}\s*г\.?",
    "service_data": r"^заявление\s+принял[:]?.*",
    "metadata": r"(qr-код содержит|эцп|mailto:|подписал:|единый\s+реестр|ис\s+«единый\s+реестр)"
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,:;()\[\]@-]", "", text)
    return text.strip()


def _chunk_by_sections(
    text: str,
    sections: Dict[str, str],
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    chunks = []
    section_map = {}
    group_map = {}

    # создаём безопасные имена групп
    for idx, (title, regex) in enumerate(sections.items()):
        group = f"SECTION_{idx}"
        section_map[group] = title
        group_map[title] = group

    try:
        pattern = re.compile(
            "|".join(f"(?P<{group}>{regex})" for group, regex in zip(group_map.values(), sections.values())),
            re.MULTILINE | re.IGNORECASE
        )
    except re.error as e:
        print(f"[regex compile error]: {e}")
        return []

    matches = list(pattern.finditer(text))

    for i, match in enumerate(matches):
        group = match.lastgroup
        title = section_map.get(group, "unknown")
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < MIN_LEN and title not in ("signature", "metadata", "service_data"):
            continue

        chunk_type = SECTION_TO_TYPE.get(title, "other")
        chunk_subtype = title.lower().replace(" ", "_")

        chunks.append({
            "title": title.capitalize(),
            "chunk_type": chunk_type,
            "chunk_subtype": chunk_subtype,
            "text": chunk_text,
            "filetype": filetype,
            "case_id": case_id,
            "document_id": document_id,
            "user_id": user_id,
            "confidence": 1.0,
            "hash": hashlib.md5(chunk_text.encode("utf-8")).hexdigest(),
            "semantic_hash": hashlib.md5(normalize_text(chunk_text).encode("utf-8")).hexdigest(),
            "position": i + 1,
            "source_page": -1
        })

    return chunks


def post_process_chunks(chunks: List[Dict]) -> List[Dict]:
    """Фильтрация и обогащение чанков."""
    processed = []
    seen_hashes = set()
    position = 1

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if len(text) < MIN_LEN and chunk.get("chunk_type") not in ("signature", "metadata", "receipt"):
            continue

        chunk_hash = chunk.get("hash") or hashlib.md5(text.encode("utf-8")).hexdigest()
        if chunk_hash in seen_hashes:
            continue
        seen_hashes.add(chunk_hash)

        semantic_hash = chunk.get("semantic_hash") or hashlib.md5(normalize_text(text).encode("utf-8")).hexdigest()

        chunk.update({
            "hash": chunk_hash,
            "semantic_hash": semantic_hash,
            "confidence": 1.0,
            "position": position,
            "source_page": chunk.get("source_page", -1),
            "chunk_subtype": chunk.get("chunk_subtype", chunk.get("title", "").lower().replace(" ", "_"))
        })

        processed.append(chunk)
        position += 1

    return processed


def chunk_zayavlenie(
    text: str,
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    return _chunk_by_sections(text, SECTION_PATTERNS, filetype, document_id, case_id, user_id)
