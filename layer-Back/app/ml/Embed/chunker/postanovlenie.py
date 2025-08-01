from typing import List, Dict
from .utils import _chunk_by_sections

def chunk_postanovlenie(text: str, document_id: int, case_id: int, user_id: int) -> List[Dict]:
    sections = {
        "Заголовок": r"^Постановление.*?$",
        "Вводная часть": r"^Рассмотрев.*?$",
        "Фактическая часть": r"^Установлено.*?$",
        "Юридическая оценка": r"^Квалифицируется.*?$|^Деяние.*?по.*?$",
        "Резолютивная часть": r"^ПОСТАНОВИЛ.*?$",
        "Права подозреваемого": r"^Права.*?разъяснены.*?$",
        "Подписи": r"^Следователь.*?$|^Подпись.*?$"
    }
    return _chunk_by_sections(text, sections, "постановление", document_id, case_id, user_id)
