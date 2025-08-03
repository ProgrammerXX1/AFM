import hashlib
import re
from typing import Dict, List, Optional
from app.ml.Embed.chunker.postprocess import generic_post_process_chunks
MIN_LEN = 100

SECTIONS = {
    "title": r"^Протокол.*?допроса.*?$",
    "header": r"^Следователь.*?допросил.*?$",
    "identity_info": r"^Фамилия.*?:.*?$",
    "rights_notice": r"^Права.*?обязанности.*?$",
    "warning_notice": r"предупрежден[а-я\s]+об\s+уголовной\s+ответственности",
    "testimony_intro": r"^Показания желаю давать.*?$|^По существу.*?$",
    "testimony_fact": r"^По обстоятельствам дела.*?$|^Также.*?поясняю.*?$",
    "testimony_impact": r"(ущерб в размере|в сумме).*?тенге",
    "conclusion": r"^На этом допрос.*?окончен.*?$",
    "signature_intro": r"^Потерпевший.*?:.*?$",
    "signature_final": r"^Документ подготовил и подписал.*?$",
    "tech_metadata": r"QR-код содержит|ИС ЭРА"
}

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())

def get_subtype(chunk_type: str) -> str:
    if "testimony_" in chunk_type:
        return chunk_type.replace("testimony_", "")
    elif chunk_type in {"signature_intro", "signature_final"}:
        return chunk_type.split("_")[1]
    return ""

def chunk_protokol(text: str, filetype: str, document_id: int, case_id: int, user_id: int) -> List[Dict]:
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
        chunk_subtype = get_subtype(chunk_type)
        confidence = 0.95 if chunk_type not in {"tech_metadata", "signature_final"} else 0.75

        hash_raw = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()
        hash_semantic = hashlib.md5(normalize_text(chunk_text).encode("utf-8")).hexdigest()

        chunks.append({
            "title": f"Допрос_chunk_{idx + 1}",
            "chunk_type": chunk_type if not chunk_type.startswith("testimony_") else "testimony",
            "chunk_subtype": chunk_subtype,
            "text": chunk_text,
            "filetype": filetype,
            "case_id": case_id,
            "document_id": document_id,
            "user_id": user_id,
            "confidence": confidence,
            "hash": hash_raw,
            "semantic_hash": hash_semantic,
            "position": idx + 1,
            "source_page": -1
        })

    return chunks

TESTIMONY_SUBTYPES = {
    "fact": [
        r"по обстоятельствам дела",
        r"также.*?поясняю",
        r"изложенное соответствует действительности"
    ],
    "damage": [
        r"(ущерб в размере|ущерб на сумму).*?тенге",
        r"причинён материальный ущерб",
        r"стоимость.*?составила"
    ],
    "participant": [
        r"видел.*?лицо",
        r"опознал",
        r"подозреваемый.*?совершил"
    ],
    "intro": [
        r"показания желаю давать",
        r"по существу могу пояснить"
    ]
}

def auto_label_testimony(text: str) -> Optional[str]:
    text = text.lower()
    for label, patterns in TESTIMONY_SUBTYPES.items():
        for pat in patterns:
            if re.search(pat, text):
                return label
    return None

def post_process_chunks(chunks: List[Dict]) -> List[Dict]:
    processed = []
    buffer = []
    current_position = 1

    def flush_buffer(ref_chunk: Dict):
        nonlocal current_position
        if not buffer:
            return
        joined = "\n\n".join(buffer)
        if len(joined) < MIN_LEN:
            return
        processed.append({
            **ref_chunk,
            "text": joined,
            "chunk_type": "testimony",
            "chunk_subtype": auto_label_testimony(joined) or "combined",
            "position": current_position,
            "hash": hashlib.md5(joined.encode("utf-8")).hexdigest(),
            "semantic_hash": hashlib.md5(normalize_text(joined).encode("utf-8")).hexdigest(),
            "source_page": ref_chunk.get("source_page", -1)
        })
        current_position += 1
        buffer.clear()

    for chunk in chunks:
        chunk_type = chunk.get("chunk_type", "")
        text = chunk.get("text", "").strip()

        if chunk_type == "testimony":
            buffer.append(text)
        else:
            flush_buffer(chunk)
            chunk["position"] = current_position
            chunk["semantic_hash"] = hashlib.md5(normalize_text(text).encode("utf-8")).hexdigest()
            if chunk["chunk_type"] == "testimony":
                chunk["chunk_subtype"] = auto_label_testimony(text) or "unspecified"
            chunk["source_page"] = chunk.get("source_page", -1)
            processed.append(chunk)
            current_position += 1

    flush_buffer(chunks[-1] if chunks else {})
    return generic_post_process_chunks(processed)
