from app.ml.chunker import split_text_to_chunks
from app.ml.embedder import get_embedding
from app.ml.weaviate_client import save_to_weaviate, client

def index_full_document(title: str, text: str, filetype: str, case_id: int):
    """Индексация документа с разбиением на чанки."""
    try:
        if not client.is_connected():
            print("🔌 Подключаемся к Weaviate...")
            client.connect()

        chunks = split_text_to_chunks(text)
        chunk_count = len(chunks)
        print(f"📑 Разбито на {chunk_count} чанков для файла {title}")

        for i, chunk in enumerate(chunks):
            try:
                vector = get_embedding(chunk)
                save_to_weaviate(
                    title=f"{title}_chunk_{i+1}",
                    text=chunk,
                    filetype=filetype,
                    case_id=case_id,
                    vector=vector
                )
            except Exception as e:
                print(f"❌ Ошибка при индексации чанка {i+1} файла {title}: {str(e)}")
                continue
    except Exception as e:
        print(f"❌ Ошибка при индексации документа {title}: {str(e)}")
        raise

from weaviate.classes.query import Filter

def search_similar_chunks(question: str, case_id: int, k: int = 5):
    """Поиск похожих чанков по вопросу и case_id."""
    try:
        if not client.is_connected():
            print("🔌 Подключаемся к Weaviate...")
            client.connect()

        question_vector = get_embedding(question)
        collection = client.collections.get("Document")

        result = collection.query.near_vector(
            near_vector=question_vector,
            filters=Filter.by_property("case_id").equal(case_id),
            limit=k
        )

        return [obj.properties for obj in result.objects]

    except Exception as e:
        print(f"❌ Ошибка при поиске чанков: {str(e)}")
        return []
