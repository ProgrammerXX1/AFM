import hashlib
import re
from collections import defaultdict
from typing import List, Dict

BLACKLIST_PATTERNS = [
    r"документ подготовил.*подписал",
    r"заявление с моих слов.*верно",
    r"права и обязанности.*разъяснены",
    r"копию постановления получил",
    r"подозреваемый.*уведомлен",
]

def matches_blacklist(text: str) -> bool:
    text = text.lower()
    for pat in BLACKLIST_PATTERNS:
        if re.search(pat, text):
            return True
    return False

def generic_post_process_chunks(chunks: List[Dict]) -> List[Dict]:
    seen_semantic = set()
    grouped = defaultdict(list)
    result = []
    position = 1

    for ch in chunks:
        text = ch.get("text", "").strip()
        if not text:
            continue

        if len(text) < 200 and matches_blacklist(text):
            continue

        sem_hash = ch.get("semantic_hash")
        if sem_hash in seen_semantic:
            continue
        seen_semantic.add(sem_hash)

        key = f"{ch.get('chunk_type')}_{sem_hash}"
        grouped[key].append(ch)

    for group in grouped.values():
        best = max(group, key=lambda x: x.get("confidence", 0))
        best["position"] = position
        result.append(best)
        position += 1

    return result

def generic_post_process_for_rerank(chunks: List[Dict], min_len=50) -> List[Dict]:
    from collections import defaultdict
    seen_semantic = set()
    grouped = defaultdict(list)
    result = []
    position = 1

    for ch in chunks:
        text = ch.get("text", "").strip()
        if not text:
            continue

        sem_hash = ch.get("semantic_hash") or hashlib.md5(text.encode()).hexdigest()
        if sem_hash in seen_semantic:
            continue
        seen_semantic.add(sem_hash)

        ch["position"] = position
        position += 1
        result.append(ch)

    return result
