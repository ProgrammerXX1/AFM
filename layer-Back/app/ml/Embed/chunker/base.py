import re
from typing import Dict, List
from .postanovlenie import chunk_postanovlenie
from .zayablenie import chunk_zayavlenie
from .dopros import chunk_dopros
from .protokol import chunk_protokol

MIN_LEN = 100

def chunk_by_filetype(
    text: str,
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    filetype = filetype.strip().lower()

    if filetype == "постановление":
        return chunk_postanovlenie(text, document_id, case_id, user_id)
    elif filetype == "заявление":
        return chunk_zayavlenie(text, document_id, case_id, user_id)
    elif filetype == "допрос":
        return chunk_dopros(text, document_id, case_id, user_id)
    elif filetype == "протокол":
        return chunk_protokol(text, document_id, case_id, user_id)
    else:
        return chunk_common(text, filetype, document_id, case_id, user_id)



def chunk_common(text: str, filetype: str, document_id: int, case_id: int, user_id: int) -> List[Dict]:
    pattern = re.compile(r"""
        (^ПРОТОКОЛ.*?)\n|
        (^Допрос .*?)\n|
        (^Постановление.*?)\n|
        (^Заявление.*?)\n|
        (^Фамилия.*?:.*?)\n|
        (^По существу .*?:.*?)\n|
        (^Права и обязанности.*?)\n|
        (^На этом допрос окончен.*?)\n
    """, re.MULTILINE | re.DOTALL | re.VERBOSE | re.IGNORECASE)

    matches = list(pattern.finditer(text))
    chunks = []

    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()
        if len(chunk_text) > MIN_LEN:
            chunks.append({
                "title": "Фрагмент",
                "text": chunk_text,
                "filetype": filetype,
                "case_id": case_id,
                "document_id": document_id,
                "user_id": user_id,
            })

    return chunks
