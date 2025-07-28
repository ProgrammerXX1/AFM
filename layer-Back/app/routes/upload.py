from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from pydantic import BaseModel
import fitz  # PyMuPDF

from app.db.database import get_db
from app.security.security import get_current_user
from app.models.cases import CaseModel, DocumentModel
from app.models.user import User
from app.ml.weaviate_client import ensure_schema, client
from app.ml.embedding_pipeline import index_full_document

router = APIRouter()

# Pydantic-модель для ответа GET /cases/{case_id}/documents
class DocumentResponse(BaseModel):
    id: int
    title: str
    filetype: str
    created_at: datetime
    content: str = ""

    class Config:
        from_attributes = True

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

@router.get("/{case_id}/documents", response_model=List[DocumentResponse])
async def get_documents(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка документов для указанного дела.
    
    Args:
        case_id: ID дела
        db: Сессия базы данных
        current_user: Текущий авторизованный пользователь
    
    Returns:
        Список документов с мета-данными
    """
    case = validate_case(case_id, current_user.id, db)
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "filetype": doc.filetype,
            "created_at": doc.created_at,
            "content": ""
        }
        for doc in case.documents
    ]

@router.post("/{case_id}/documents", response_model=UploadResponse)
async def upload_documents(
    case_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Загрузка документов для указанного дела с индексацией в Weaviate.

    Args:
        case_id: ID дела
        files: Список загружаемых файлов
        db: Сессия базы данных
        current_user: Текущий авторизованный пользователь

    Returns:
        Сообщение об успешной загрузке
    """
    case = validate_case(case_id, current_user.id, db)

    # Проверка лимита документов
    doc_count = len(case.documents) if case.documents else 0
    if doc_count + len(files) > 100:
        raise HTTPException(status_code=400, detail="Превышен лимит документов (100)")

    # Инициализация Weaviate
    try:
        if not client.is_connected():
            print("🔌 Подключаемся к Weaviate...")
            client.connect()
        ensure_schema()
    except Exception as e:
        print(f"❌ Ошибка при инициализации Weaviate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка инициализации Weaviate: {str(e)}")

    processed_files = 0
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

            # Сохранение в БД
            document = DocumentModel(
                title=file.filename,
                filetype=file.content_type,
                weaviate_id=None,  # Чанки хранятся отдельно
                created_at=datetime.utcnow(),
                case_id=case.id
            )
            db.add(document)
            case.documents.append(document)
            processed_files += 1
        except Exception as e:
            print(f"❌ Ошибка обработки файла {file.filename}: {str(e)}")
            continue  # Продолжаем с другими файлами

    try:
        db.commit()
    except Exception as e:
        print(f"❌ Ошибка при сохранении в БД: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения в БД: {str(e)}")

    return {"message": f"Загружено {processed_files} из {len(files)} документов успешно"}
