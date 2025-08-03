import re
import logging
from typing import Dict, List, Callable

from .postanovlenie import chunk_postanovlenie, post_process_chunks as process_postanovlenie
from .zayablenie import chunk_zayavlenie, post_process_chunks as process_zayavlenie
from .dopros import chunk_dopros, post_process_chunks as process_dopros
from .protokol import chunk_protokol, post_process_chunks as process_protokol
from .default import chunk_common, post_process_chunks as process_default

logger = logging.getLogger(__name__)


def detect_doc_type(text: str) -> str:
    """Определяет тип документа по ключевым признакам."""
    lowered = text.lower()

    if re.search(r"протокол", lowered):
        logger.info("📑 Тип документа: протокол допроса")
        return "протокол"
    elif re.search(r"\bпостановление\b", lowered):
        logger.info("📑 Тип документа: постановление (возбуждение)")
        return "постановление"
    elif "рапорт" in lowered:
        logger.info("📑 Тип документа: рапорт → допрос")
        return "допрос"
    elif re.search(r"\bдопрос\b", lowered):
        logger.info("📑 Тип документа: допрос")
        return "допрос"
    elif re.search(r"\bзаявление\b", lowered):
        logger.info("📑 Тип документа: заявление")
        return "заявление"
    elif re.search(r"\bпостановление\b", lowered):
        logger.info("📑 Тип документа: постановление")
        return "постановление"
    else:
        logger.warning("⚠️ Не удалось точно определить тип, fallback = протокол")
        return "протокол"


def chunk_by_filetype(
    text: str,
    filetype: str,
    document_id: int,
    case_id: int,
    user_id: int
) -> List[Dict]:
    """
    Вызывает нужную функцию чанкинга по типу документа.
    Поддерживает auto-определение по тексту.
    """
    filetype_original = filetype
    if not filetype or filetype.strip().lower() == "auto":
        filetype = detect_doc_type(text)
    else:
        filetype = filetype.strip().lower()
        logger.info(f"📂 Тип файла задан явно: {filetype}")

    chunk_fn_map = {
        "постановление": chunk_postanovlenie,
        "заявление": chunk_zayavlenie,
        "допрос": chunk_dopros,
        "протокол": chunk_protokol,
    }

    chunk_fn = chunk_fn_map.get(filetype, chunk_common)
    logger.debug(f"🧩 Используем функция чанкинга: {chunk_fn.__name__}")

    chunks = chunk_fn(text, filetype, document_id, case_id, user_id)

    processor = get_postprocessor(filetype)
    return processor(chunks)


def get_postprocessor(filetype: str) -> Callable[[List[Dict]], List[Dict]]:
    """Возвращает соответствующую функцию постобработки чанков."""
    filetype = filetype.strip().lower()

    processor_map = {
        "постановление": process_postanovlenie,
        "заявление": process_zayavlenie,
        "допрос": process_dopros,
        "протокол": process_protokol,
    }

    processor = processor_map.get(filetype, process_default)
    logger.debug(f"🛠 Постобработка: {processor.__name__}")
    return processor
