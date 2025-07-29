import logging

logger = logging.getLogger(__name__)

def split_text_to_chunks(text: str, max_chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Разбивает текст на чанки с перекрытием."""
    try:
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1

            if current_length >= max_chunk_size:
                chunks.append(" ".join(current_chunk))
                overlap_words = " ".join(current_chunk[-int(overlap/5):])
                current_chunk = overlap_words.split()
                current_length = len(overlap_words)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.debug(f"Текст разбит на {len(chunks)} чанков")
        return chunks
    except Exception as e:
        logger.error(f"Ошибка при разбиении текста на чанки: {str(e)}")
        raise