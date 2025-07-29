from fastapi import APIRouter, Query, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
import fitz  # PyMuPDF
import logging

from app.db.database import get_db
from app.security.security import get_current_user
from app.models.cases import CaseModel, DocumentModel
from app.models.user import User
from app.core.weaviate_client import ensure_schema, client
from app.ml.embedding_pipeline import index_full_document
from app.ml.embedding_pipeline import search_similar_chunks
from app.ml.pipeline import answer_query

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

            # Индексация в Weaviate
            index_full_document(
                title=file.filename,
                text=text,
                filetype=file.content_type,
                case_id=case.id
            )

            # Подготовка документа для БД
            document = DocumentModel(
                title=file.filename,
                filetype=file.content_type,
                created_at=datetime.utcnow(),
                case_id=case.id
            )
            documents.append(document)
            processed_files += 1
        except Exception as e:
            logger.error(f"Ошибка обработки файла {file.filename}: {str(e)}")
            continue

    # Сохранение всех документов одним коммитом
    try:
        db.add_all(documents)
        db.commit()
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения в БД")

    return {"message": f"Загружено {processed_files} из {len(files)} документов успешно"}

@router.get("/cases/{case_id}/search")
async def semantic_search(
    case_id: int,
    q: str = Query(..., description="Ваш поисковый запрос"),
    current_user: User = Depends(get_current_user)
):
    try:
        logger.info(f"🔎 Запрос: '{q}' для дела #{case_id}")
        results = search_similar_chunks(query=q, case_id=case_id, k=10)
        return {"results": results}
    except Exception as e:
        logger.exception("❌ Ошибка при выполнении семантического поиска")
        raise HTTPException(status_code=500, detail=str(e))

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str

@router.post("/ask/{case_id}", response_model=AnswerResponse)
async def ask(case_id: int, request: QuestionRequest):
    """
    Генерация юридического ответа на вопрос по делу с заданным case_id.
    """
    try:
        answer = answer_query(case_id, request.question)
        return {"answer": answer}
    except Exception as e:
        logger.exception("Ошибка при генерации ответа")
        raise HTTPException(status_code=500, detail="Ошибка генерации ответа")