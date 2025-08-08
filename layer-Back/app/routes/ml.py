from fastapi import APIRouter, Query, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import fitz  # PyMuPDF
import logging
import os
import httpx
from dotenv import load_dotenv
import tiktoken
from fastapi.responses import PlainTextResponse
from pathlib import Path
import re
from app.db.database import get_db
from app.security.security import get_current_user
from app.models.cases import CaseModel, DocumentModel
from app.models.user import User
from app.ml.Embed.pipeline import index_full_document, search_similar_chunks
from app.ml.Generation.generator import generate_investigation_plan

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic-модели для ответов
class DocumentResponse(BaseModel):
    id: int
    title: str
    filetype: str
    created_at: datetime
    content: str = ""

    model_config = ConfigDict(from_attributes=True)

class UploadResponse(BaseModel):
    message: str

# Конфигурация для работы с токенами
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL")
GENERATOR_URL = os.getenv("GENERATOR_URL")
MODEL_ENCODING = "cl100k_base"  # Для GPT-3/GPT-4 моделей

# Настройка директории для хранения документов
STORAGE_DIR = Path("storage/docs")

# Функция для подсчета токенов
def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding(MODEL_ENCODING)
    tokens = encoding.encode(text)
    return len(tokens)

# Функция для извлечения текста из файлов

def clean_text(text: str) -> str:
    """Очистка текста: удаление лишних пробелов и пустых строк."""
    # Убираем пробелы в начале и конце текста
    text = text.strip()
    # Убираем несколько пробелов подряд, заменяя их на один
    text = re.sub(r'\s+', ' ', text)
    # Убираем лишние пустые строки, чтобы документы шли подряд
    text = re.sub(r'(\n\s*)+', '\n', text)  # Преобразуем несколько пустых строк в одну
    return text

def extract_text(file: UploadFile, content: bytes) -> str:
    """Извлечение текста из файла."""
    if file.content_type == "application/pdf":
        import fitz  # PyMuPDF
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

@router.post("/cases/{case_id}/documents", response_model=UploadResponse)
async def upload_documents(
    case_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Загрузка документов и сохранение текста всех файлов в один общий файл."""
    case = validate_case(case_id, current_user.id, db)

    # Проверка лимита документов
    if len(case.documents) + len(files) > 100:
        raise HTTPException(status_code=400, detail="Превышен лимит документов (100)")

    all_text = ""
    processed_files = 0
    documents = []

    # Директория для хранения файлов
    doc_folder = STORAGE_DIR / str(case.id)
    doc_folder.mkdir(parents=True, exist_ok=True)

    # Путь для объединенного файла
    combined_txt_path = doc_folder / f"combined_documents_{case.id}.txt"

    # Проверяем, существует ли уже общий файл
    if combined_txt_path.exists():
        logger.info(f"Файл {combined_txt_path} уже существует. Пропускаем запись.")
    else:
        # Если файл не существует, обрабатываем файлы
        for file in files:
            try:
                content = await file.read()
                text = extract_text(file, content)

                # Очистка текста от лишних пробелов и промежутков
                cleaned_text = clean_text(text)

                # Создание записи в БД
                document = DocumentModel(
                    title=file.filename,
                    filetype=file.content_type,
                    created_at=datetime.now(timezone.utc),
                    case_id=case.id
                )
                db.add(document)
                db.flush()

                # Добавление очищенного текста в общий файл
                all_text += f"\n\n--- Документ: {file.filename} ---\n\n"
                all_text += cleaned_text

                documents.append(document)
                processed_files += 1

            except Exception as e:
                logger.error(f"Ошибка обработки файла {file.filename}: {str(e)}")
                db.rollback()
                continue

        # Сохраняем общий файл только если он не существует
        try:
            with open(combined_txt_path, "w", encoding="utf-8") as f:
                f.write(all_text)
            logger.info(f"Общий файл успешно сохранен в {combined_txt_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении общего файла: {str(e)}")
            raise HTTPException(status_code=500, detail="Ошибка при сохранении общего файла")

    try:
        db.commit()
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка сохранения в БД")

    return {"message": f"Загружено {processed_files} из {len(files)} документов успешно"}

@router.get("/cases/{case_id}/prompt")
async def generate_and_analyze_prompt(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Генерирует промпт из одного объединенного файла и передает в Ollama или llama.cpp сервер."""
    
    # Проверка существования дела и прав доступа текущего пользователя
    case = validate_case(case_id, current_user.id, db)

    # Путь к общему файлу
    combined_txt_path = STORAGE_DIR / str(case_id) / f"combined_documents_{case_id}.txt"

    if not combined_txt_path.exists():
        raise HTTPException(status_code=404, detail="Общий файл с документами не найден")

    try:
        with open(combined_txt_path, "r", encoding="utf-8") as f:
            full_prompt = f.read().strip()
    except Exception as e:
        logger.error(f"Не удалось прочитать общий файл {combined_txt_path}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка чтения общего файла")

    if not full_prompt:
        raise HTTPException(status_code=400, detail="Файлы пусты или не содержат текста")

    # Подсчет токенов в промпте
    token_count = count_tokens(full_prompt)

    MAX_TOKENS = 32768  # Лимит для вашей модели

    # Проверка на превышение лимита токенов
    if token_count > MAX_TOKENS:
        raise HTTPException(status_code=400, detail=f"Токенов слишком много ({token_count}), максимальный лимит: {MAX_TOKENS}.")

    # Инструкция для модели с требованием развернутого ответа не менее 200 слов
    instruction = """
    Ты юридический помощник. Проанализируй материалы дела и выдай:
    - 📌 Квалификацию правонарушения
    - 📎 Статью и часть УК РК
    - 🛠 План действий для следствия

    Пожалуйста, предоставь развернутый ответ, который должен быть не менее 200 слов.
    """

    final_prompt = f"{full_prompt}\n\n{instruction.strip()}"

    try:
        async with httpx.AsyncClient(timeout=2400.0) as client:
            payload = {
                "model": GENERATOR_MODEL,
                "prompt": final_prompt,
                "n_predict": 1500,  # Увеличиваем количество токенов для длинного ответа (можно настроить)
                "temperature": 0.7,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "stream": False
            }
            response = await client.post(GENERATOR_URL, json=payload)
            response.raise_for_status()
            result = response.json()

            model_reply = result.get("content") or result.get("response") or result.get("text", "[Пустой ответ]")

    except Exception as e:
        logger.error(f"Ошибка при генерации: {e}")
        raise HTTPException(status_code=502, detail="Модель не ответила")

    # Проверка длины ответа на 200 слов
    word_count = len(model_reply.split())

    if word_count < 200:
        logger.warning(f"Ответ модели меньше 200 слов: {word_count} слов. Попытка перегенерации.")
        # При необходимости, можно повторить запрос с увеличением длины ответа или другой логикой
        return {
            "case_id": case_id,
            "documents_included": 1,
            "documents_missing": [],
            "generator_model": GENERATOR_MODEL,
            "token_count": token_count,
            "result": f"Ответ модели слишком короткий ({word_count} слов), требуется перегенерация."
        }

    # Возвращаем не только результат, но и количество токенов
    return {
        "case_id": case_id,
        "documents_included": 1,  # Поскольку теперь это один объединенный файл
        "documents_missing": [],
        "generator_model": GENERATOR_MODEL,
        "token_count": token_count,  # Добавляем количество токенов в ответ
        "result": model_reply.strip()
    }



@router.get("/cases/{case_id}/search_changs")
async def semantic_search(
    case_id: int,
    q: str = Query(..., description="Ваш поисковый запрос"),
    current_user: User = Depends(get_current_user)
):
    """Семантический поиск по документам."""
    try:
        logger.info(f"Запрос: '{q}' для дела #{case_id}")
        results = search_similar_chunks(query=q, case_id=case_id, k=5)
        return {"results": results}
    except Exception as e:
        logger.exception("Ошибка при поиске")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/generate/qualification/{case_id}", response_class=PlainTextResponse)
async def generate_qualification(case_id: int):
    """Генерация постановления о квалификации правонарушения."""
    try:
        logger.info(f"Генерация постановления для case_id={case_id}")
        result = generate_investigation_plan(case_id)
        return result
    except Exception:
        logger.exception("Ошибка генерации постановления")
        raise HTTPException(status_code=500, detail="Ошибка генерации постановления")
