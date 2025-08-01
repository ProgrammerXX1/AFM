from typing import List, Dict
from .utils import _chunk_by_sections

def chunk_zayavlenie(text: str, document_id: int, case_id: int, user_id: int) -> List[Dict]:
    sections = {
        "Адресат": r"^Следователю.*?$",
        "Данные заявителя": r"^От[:]?.*?$|^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.",
        "Заголовок": r"^ЗАЯВЛЕНИЕ.*?$",
        "Основной текст": r"^Об.*?|^От.*?отказыва.*?|^Я.*?",
        "Подпись заявителя": r"^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.\s+\d{2}\.\d{2}\.\d{4}",
        "Принято следователем": r"^Заявление принял[:]?.*?$",
        "Служебные данные": r"QR-код содержит|ЭЦП|mailto:erdr@kgp.kz"
    }
    return _chunk_by_sections(text, sections, "заявление", document_id, case_id, user_id)
