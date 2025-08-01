import re
from typing import Dict, List
MIN_LEN = 100
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
            chunks.append({
                "title": title,
                "text": chunk_text,
                "filetype": filetype,
                "case_id": case_id,
                "document_id": document_id,
                "user_id": user_id,
            })

    return chunks