from app.core.weaviate_client import client
import logging

logger = logging.getLogger(__name__)

def clear_weaviate_documents():
    """Удаляет ВСЕ объекты из коллекции 'Document' по UUID."""
    try:
        if not client.is_connected():
            logger.info("🔌 Подключаемся к Weaviate...")
            client.connect()

        collection = client.collections.get("Document")

        logger.info("📥 Получаем список всех объектов в коллекции...")
        all_objects = collection.query.fetch_objects(limit=9999)

        if not all_objects.objects:
            logger.info("ℹ️ Коллекция уже пуста.")
            return 0

        deleted_count = 0
        for obj in all_objects.objects:
            try:
                collection.data.delete_by_id(obj.uuid)
                logger.info(f"🗑️ Удалён: {obj.uuid}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить {obj.uuid}: {e}")

        logger.info(f"✅ Всего удалено: {deleted_count}")
        return deleted_count

    except Exception as e:
        logger.error(f"❌ Ошибка при очистке Weaviate: {e}")
        return 0


if __name__ == "__main__":
    deleted = clear_weaviate_documents()
    print(f"✅ Удалено: {deleted}")