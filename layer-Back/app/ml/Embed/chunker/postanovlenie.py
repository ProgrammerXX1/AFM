import re
import hashlib
from typing import List, Dict

SECTION_TO_TYPE = {
    "title": "title",
    "intro": "intro",
    "identity_info": "identity_info",
    "fact": "fact",
    "decision": "decision",
    "final_notice": "decision",
    "rights_notice": "rights_notice",
    "signature": "signature",
    "technical_signature": "metadata",
}

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"mailto:[\w@.]+", "", text)
    text = re.sub(r"(qr-код.*|ис «единый реестр.*?)", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,:;()\[\]@-]", "", text)
    return text.strip()

def split_long_text(text: str, chunk_template: Dict, max_len: int = 1500) -> List[Dict]:
    chunks = []
    paragraphs = re.split(r"(?<=\d\))", text)
    buffer = ""
    count = 1

    for para in paragraphs:
        buffer += para
        if len(buffer) > max_len:
            new_chunk = chunk_template.copy()
            new_chunk["text"] = buffer.strip()
            new_chunk["chunk_subtype"] = f"{chunk_template['chunk_type']}_part_{count}"
            new_chunk["semantic_hash"] = hashlib.md5(normalize_text(buffer).encode()).hexdigest()
            new_chunk["hash"] = hashlib.md5(buffer.encode()).hexdigest()
            chunks.append(new_chunk)
            buffer = ""
            count += 1

    if buffer.strip():
        new_chunk = chunk_template.copy()
        new_chunk["text"] = buffer.strip()
        new_chunk["chunk_subtype"] = f"{chunk_template['chunk_type']}_part_{count}"
        new_chunk["semantic_hash"] = hashlib.md5(normalize_text(buffer).encode()).hexdigest()
        new_chunk["hash"] = hashlib.md5(buffer.encode()).hexdigest()
        chunks.append(new_chunk)

    return chunks

def chunk_postanovlenie(
    text: str,
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    sections = {
        "title": r"(?i)^постановление.*?$",
        "intro": r"(?i)^г\.?\s?[а-яёa-z-]{2,}(,|\s).*?$",
        "identity_info": r"(?i)^следователь\b.*?рассмотрев.*?$",
        "fact": r"(?i)^установ(?:лено|ил):.*?$",
        "decision": r"(?i)^постанов(?:ил|ляю):.*?$",
        "final_notice": r"(?i)^о принятом решении уведомить.*?$",
        "rights_notice": r"(?i)(разъяснены.*?права.*?|права и обязанности.*?разъяснены.*?)",
        "signature": r"(?i)^постановление объявил.*?$|потерпевший.*?подпись|копию.*?получил|подписал:|настоящ.*?постановление.*?объявлено",
        "technical_signature": r"(?i)(QR-код.*|ИС «единый реестр|mailto:)",
    }

    return _chunk_by_sections(text, sections, filetype, document_id, case_id, user_id)

def _chunk_by_sections(
    text: str,
    sections: Dict[str, str],
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    pattern = re.compile("|".join(f"(?P<{key}>{regex})" for key, regex in sections.items()), re.MULTILINE)
    matches = list(pattern.finditer(text))
    chunks = []
    seen = set()

    for i, match in enumerate(matches):
        key = match.lastgroup
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if not chunk_text or len(chunk_text) < 50:
            continue

        chunk_type = SECTION_TO_TYPE.get(key, "other")
        if chunk_type not in SECTION_TO_TYPE.values():
            chunk_type = "other"

        chunk_template = {
            "title": key.capitalize(),
            "chunk_type": chunk_type,
            "chunk_subtype": key if key in SECTION_TO_TYPE else chunk_type,
            "text": chunk_text,
            "filetype": filetype,
            "case_id": case_id,
            "document_id": document_id,
            "user_id": user_id,
            "confidence": 1.0,
            "hash": hashlib.md5(chunk_text.encode()).hexdigest(),
            "semantic_hash": hashlib.md5(normalize_text(chunk_text).encode()).hexdigest(),
            "position": -1,
            "source_page": -1,
        }

        if chunk_template["semantic_hash"] in seen:
            continue
        seen.add(chunk_template["semantic_hash"])

        if len(chunk_text) > 1500:
            chunks.extend(split_long_text(chunk_text, chunk_template))
        else:
            chunks.append(chunk_template)

    return chunks

def post_process_chunks(chunks: List[Dict]) -> List[Dict]:
    valid_types = set(SECTION_TO_TYPE.values())
    seen_semantic = set()
    result = []
    position = 1

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text or (len(text) < 100 and chunk.get("chunk_type") not in ("signature", "metadata")):
            continue

        sem_hash = chunk.get("semantic_hash")
        if sem_hash in seen_semantic:
            continue
        seen_semantic.add(sem_hash)

        low_text = text.lower()
        original_type = chunk.get("chunk_type")

        # 🔄 Исправление невалидных типов
        if original_type not in valid_types:
            if original_type == "signature_final":
                chunk["chunk_type"] = "signature"
                chunk["chunk_subtype"] = "signature_final"
            elif original_type == "signature_intro":
                chunk["chunk_type"] = "signature"
                chunk["chunk_subtype"] = "signature_intro"
            elif original_type == "tech_metadata":
                chunk["chunk_type"] = "metadata"
                chunk["chunk_subtype"] = "qr_signature"
            else:
                chunk["chunk_type"] = "other"

        # 🧠 Назначение семантических подтипов
        if "о принятом решении уведомить" in low_text:
            chunk["chunk_type"] = "decision"
            chunk["chunk_subtype"] = "final_notice"
        elif "имеет право" in low_text:
            chunk["chunk_type"] = "rights_notice"
            chunk["chunk_subtype"] = "detailed_rights"
        elif "обязан" in low_text:
            chunk["chunk_type"] = "rights_notice"
            chunk["chunk_subtype"] = "obligations"
        elif ("разъяснен" in low_text or "разъяснены" in low_text) and "права" in low_text:
            chunk["chunk_type"] = "rights_notice"
            chunk["chunk_subtype"] = "confirmation"
        elif "подписал" in low_text and "копию" in low_text:
            chunk["chunk_type"] = "signature"
            chunk["chunk_subtype"] = "signature_full"
        elif "копию" in low_text or "объявлено" in low_text:
            chunk["chunk_type"] = "signature"
            chunk["chunk_subtype"] = "signature_notice"
        elif chunk.get("chunk_type") == "signature":
            if not chunk.get("chunk_subtype"):
                chunk["chunk_subtype"] = "signature_author" if "подписал" in low_text else "signature_other"
        elif chunk.get("chunk_type") == "metadata":
            chunk["chunk_subtype"] = "qr_signature"

        # ✅ Fallback subtype
        if not chunk.get("chunk_subtype") or chunk["chunk_subtype"] is None:
            chunk["chunk_subtype"] = chunk["chunk_type"]

        # 🚫 Финальная валидация
        if chunk["chunk_type"] not in valid_types:
            raise ValueError(f"❌ Недопустимый chunk_type: {chunk['chunk_type']} в чанке:\n{text[:200]}...")

        # ➕ Назначение позиции
        chunk["position"] = position
        result.append(chunk)
        position += 1

    if not result:
        raise ValueError("⚠️ Все чанки были отфильтрованы — проверь правила или исходный текст.")
    return result
