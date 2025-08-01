from typing import List, Dict
from .utils import _chunk_by_sections

def chunk_dopros(text: str, document_id: int, case_id: int, user_id: int) -> List[Dict]:
    sections = {
        "Заголовок": r"^Протокол.*?допроса.*?$",
        "Личные данные": r"^Фамилия.*?:.*?$",
        "Права и обязанности": r"^Права.*?обязанности.*?$",
        "Суть показаний": r"^По существу.*?$",
        "Завершение": r"^На этом допрос окончен.*?$",
        "Подпись": r"^Следователь.*?$|^Подпись.*?$"
    }
    return _chunk_by_sections(text, sections, "допрос", document_id, case_id, user_id)
