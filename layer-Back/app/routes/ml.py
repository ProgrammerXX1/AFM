from fastapi import APIRouter, Query, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import fitz  # PyMuPDF
import logging
import json
from app.db.database import get_db
from app.security.security import get_current_user
from app.models.cases import CaseModel, DocumentModel
from app.models.user import User
from app.ml.Embed.pipeline import index_full_document
from app.ml.Embed.pipeline import search_similar_chunks
router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic-модель для ответа GET /cases/{case_id}/documents
class DocumentResponse(BaseModel):
    id: int
    title: str
    filetype: str
    created_at: datetime
    content: str = ""

    model_config = ConfigDict(from_attributes=True)

# Pydantic-модель для ответа POST /cases/{case_id}/documents
class UploadResponse(BaseModel):
    message: str

def extract_text(file: UploadFile, content: bytes) -> str:
    """Извлечение текста из файла."""
    if file.content_type == "application/pdf":
        with fitz.open(stream=content, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    return content.decode("utf-8", errors="ignore")

def validate_case(case_id: int, user_id: int, db: Session) -> CaseModel:
    """Проверка существования дела и прав доступа."""
    case = db.query(CaseModel).filter(
        CaseModel.id == case_id,
        CaseModel.user_id == user_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    return case

@router.get("/cases/{case_id}/documents", response_model=List[DocumentResponse])
async def get_documents(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка документов для указанного дела."""
    case = validate_case(case_id, current_user.id, db)
    return case.documents

@router.post("/cases/{case_id}/documents", response_model=UploadResponse)
async def upload_documents(
    case_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Загрузка документов для указанного дела с индексацией в Weaviate."""
    case = validate_case(case_id, current_user.id, db)

    # Проверка лимита документов
    doc_count = len(case.documents) if case.documents else 0
    if doc_count + len(files) > 100:
        raise HTTPException(status_code=400, detail="Превышен лимит документов (100)")

    processed_files = 0
    documents = []

    for file in files:
        try:
            content = await file.read()
            text = extract_text(file, content)

            # 🧩 Создание записи в БД
            document = DocumentModel(
                title=file.filename,
                filetype=file.content_type,
                created_at=datetime.now(timezone.utc),
                case_id=case.id
            )
            db.add(document)
            db.flush()  # ← Получаем document.id

            # ✅ Индексация чанков с учетом user_id и doc_type="auto"
            index_full_document(
                title=file.filename,
                text=text,
                filetype=file.content_type,
                user_id=current_user.id,
                case_id=case.id,
                document_id=document.id,
                doc_type="auto"
            )

            documents.append(document)
            processed_files += 1

        except Exception as e:
            logger.error(f"❌ Ошибка обработки файла {file.filename}: {str(e)}")
            db.rollback()
            continue

    # ✅ Финальный коммит
    try:
        db.commit()
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении в БД: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка сохранения в БД")

    return {"message": f"Загружено {processed_files} из {len(files)} документов успешно"}


@router.get("/cases/{case_id}/search_changs")
async def semantic_search(
    case_id: int,
    q: str = Query(..., description="Ваш поисковый запрос"),
    current_user: User = Depends(get_current_user)
):
    try:
        logger.info(f"🔎 Запрос: '{q}' для дела #{case_id}")
        results = search_similar_chunks(query=q, case_id=case_id, k=5)
        return {"results": results}
    except Exception as e:
        logger.exception("❌ Ошибка при выполнении семантического поиска")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cases/{case_id}/chunks")
async def get_all_chunks_by_case(
    case_id: int,
    current_user: User = Depends(get_current_user)
):
    try:
        logger.info(f"📥 Получение всех чанков по делу #{case_id}")

        chunks = get_chunks_by_case_id(case_id=case_id)
        logger.info(f"📦 Найдено {len(chunks)} чанков")

        return {"results": chunks}

    except Exception as e:
        logger.exception("❌ Ошибка при получении чанков")
        raise HTTPException(status_code=500, detail="Ошибка при получении чанков")


class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str

def truncate_context(context: str, max_chars: int = 16000) -> str:
    """Обрезает текст до лимита символов (подходит для LLaMA 7B в Q4/Q5)."""
    if len(context) <= max_chars:
        return context
    return context[:max_chars] + "\n\n...контекст обрезан из-за размера..."


import re  # 👈 добавь в начало файла, если ещё не импортирован
from typing import List, Dict, Any
import re
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.weaviate_client import WeaviateClient
from app.ml.Generation.retriever import get_chunks_by_case_id
from app.ml.Generation.generator import generate_investigation_plan
from fastapi.responses import JSONResponse
logger = logging.getLogger(__name__)
from fastapi.responses import PlainTextResponse


@router.get("/generate/qualification/{case_id}", response_class=PlainTextResponse)
async def generate_qualification(case_id: int):
    """
    Генерация постановления о квалификации уголовного правонарушения.
    Возвращает полный юридический текст как обычный документ.
    """
    try:
        logger.info(f"📥 Генерация постановления для case_id={case_id}")

        # Получаем чанки
        chunk_types = ["testimony", "conclusion", "body", "warning_notice", "rights_notice"]
        chunks = get_chunks_by_case_id(case_id=case_id)
        filtered_chunks = [c for c in chunks if c.get("chunk_type") in chunk_types]

        
        
        if not chunks:
            raise HTTPException(status_code=404, detail="Нет данных для генерации постановления.")

        # Склеиваем текст
        context = "\n\n".join(chunk["text"] for chunk in filtered_chunks if chunk.get("text"))
        # logger.warning("Чанки, передаваемые в генератор:\n%s", json.dumps(chunks, indent=2, ensure_ascii=False))

        # 
     
        generated_text = generate_investigation_plan(context)
        logger.warning("📤 Ответ от модели:\n%s", generated_text)


        return generated_text

    except Exception:
        logger.exception("❌ Ошибка генерации постановления")
        raise HTTPException(status_code=500, detail="Ошибка генерации постановления")