# app/ml/chunking.py
# -*- coding: utf-8 -*-
import re
import json
import statistics
from typing import Dict, List, Any, Tuple
import tiktoken

from .config import CHUNK_TOKENS, CHUNK_OVERLAP, MODEL_ENCODING
from .io_utils import storage_paths


# ---------- заголовки верхнего уровня ----------
# Матчим строку-«шапку» документа. «Р А П О Р Т» допускает пробелы между буквами.
HEAD_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^\s*ПОСТАНОВЛЕНИЕ\b.*", re.IGNORECASE), "postanovlenie"),
    (re.compile(r"^\s*ПРОТОКОЛ\b.*", re.IGNORECASE), "protokol"),
    (re.compile(r"^\s*Р\s*А\s*П\s*О\s*Р\s*Т\b.*", re.IGNORECASE), "raport"),
    (re.compile(r"^\s*УВЕДОМЛЕНИЕ\b.*", re.IGNORECASE), "uvedomlenie"),
]


def _split_by_headings(full_text: str) -> List[Dict[str, Any]]:
    """
    Разбиваем исходный текст на секции по верхним заголовкам.
    Возвращаем список секций: [{"heading": str|None, "doc_type": str, "text": str}, ...]
    Если заголовков нет — одна секция с doc_type="unknown".
    """
    lines = full_text.splitlines()
    hits: List[Tuple[int, str, str]] = []  # (line_idx, heading_text, doc_type)

    for i, ln in enumerate(lines):
        for rx, dtype in HEAD_PATTERNS:
            if rx.match(ln):
                # Берём целиком строку как "heading"
                heading = ln.strip()
                hits.append((i, heading, dtype))
                break

    if not hits:
        return [{"heading": None, "doc_type": "unknown", "text": full_text}]

    # Закрываем интервалы секций
    sections: List[Dict[str, Any]] = []
    for j, (start_idx, heading, dtype) in enumerate(hits):
        end_idx = hits[j + 1][0] if j + 1 < len(hits) else len(lines)
        body = "\n".join(lines[start_idx:end_idx]).strip()
        sections.append({"heading": heading, "doc_type": dtype, "text": body})

    return sections


def chunk_text(
    text: str,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Чанкинг с учётом верхних заголовков:
    1) сначала режем документ на секции по заголовкам (ПОСТАНОВЛЕНИЕ/ПРОТОКОЛ/Р А П О Р Т/УВЕДОМЛЕНИЕ),
    2) затем каждую секцию нарезаем по токенам с перекрытием.
    В метаданные каждого чанка кладём: doc_type, heading, section_id.
    """
    enc = tiktoken.get_encoding(MODEL_ENCODING)
    sections = _split_by_headings(text)

    chunks: List[Dict[str, Any]] = []
    global_idx = 0

    for section_id, sec in enumerate(sections):
        sec_text = sec["text"]
        ids = enc.encode(sec_text)

        start = 0
        while start < len(ids):
            end = min(start + chunk_tokens, len(ids))
            sub_ids = ids[start:end]
            sub_txt = enc.decode(sub_ids)

            chunks.append({
                "chunk_id": global_idx,
                "section_id": section_id,
                "doc_type": sec["doc_type"],
                "heading": sec["heading"],
                "text": sub_txt,
                "n_tokens": len(sub_ids),
            })
            global_idx += 1

            if end == len(ids):
                break
            start = max(0, end - overlap_tokens)

    return chunks


def tokens_stats(items: List[int]) -> str:
    if not items:
        return "n/a"
    return (
        f"min={min(items)}, "
        f"median={int(statistics.median(items))}, "
        f"max={max(items)}, "
        f"total={sum(items)}"
    )


def load_doc_chunks(case_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Детерминированная загрузка чанков:
    - файлы по возрастанию doc_id,
    - внутри файла чанки по chunk_id.
    """
    paths = storage_paths(case_id)
    chunks_dir = paths["chunks"]
    out: Dict[str, List[Dict[str, Any]]] = {}
    if not chunks_dir.exists():
        return out

    files = sorted(chunks_dir.glob("*.jsonl"), key=lambda p: int(p.stem))
    for fn in files:
        doc_id = fn.stem
        items: List[Dict[str, Any]] = []
        with fn.open("r", encoding="utf-8") as f:
            for line in f:
                items.append(json.loads(line))
        items.sort(key=lambda x: int(x.get("chunk_id", 0)))
        out[doc_id] = items
    return out
