# app/ml/pipeline.py
from app.ml.embedding_pipeline import search_similar_chunks
from app.ml.generator import generate_answer

def answer_query(case_id: int, question: str) -> str:
    try:
        docs = search_similar_chunks(question, case_id)
        context = "\n\n".join([d.properties["text"] for d in docs])
        prompt = f"Вопрос: {question}\nКонтекст:\n{context}\nОтвет:"
        return generate_answer(prompt)
    except Exception as e:
        print("❌ Ошибка в answer_query:", str(e))
        raise
