
import os

CACHE_DIR = "/"  # 🧠 Каталог временных кэшей
def clear_seen_chunks(user_id: int, case_id: int, document_id: int):
    """Удаление кэш-файлов для конкретного пользователя и документа."""
    filename = f"seen_{user_id}_{case_id}_{document_id}.json"
    path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        print(f"🗑️ Кэш удалён: {path}")
