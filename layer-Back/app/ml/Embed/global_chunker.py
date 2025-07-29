# app/ml/Embed/global_chunk_cache.py

# Хранилище уже сохранённых чанков (можно заменить на Redis или SQLite при проде)
global_chunk_set = set()

def normalize_chunk(text: str) -> str:
    """Приведение чанка к единому виду для сравнения."""
    import re
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def is_duplicate_chunk(chunk: str) -> bool:
    norm = normalize_chunk(chunk)
    return norm in global_chunk_set

def register_chunk(chunk: str):
    norm = normalize_chunk(chunk)
    global_chunk_set.add(norm)
