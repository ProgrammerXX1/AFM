import weaviate

client = weaviate.Client("http://localhost:8080")

doc_id = "31abeb45-c453-4615-b56f-f314907e6323"

exists = client.data_object.exists(doc_id)
if exists:
    print("✅ Объект найден")

    obj = client.data_object.get_by_id(doc_id)
    print("📎 UUID:", doc_id)
    print("📚 Properties:", obj.get("properties", {}))
    print("📊 Вектор:", obj.get("vector", None))
else:
    print("❌ Нет такого объекта")
