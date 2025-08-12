# -*- coding: utf-8 -*-
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
import json
import logging
from pathlib import Path

from app.db.database import get_db
from app.security.security import get_current_user
from app.models.cases import CaseModel, DocumentModel
from app.models.user import User

# локальные модули
from app.ml.config import logger, STORAGE_DIR
from app.ml.io_utils import clean_text, extract_text, count_tokens, storage_paths, write_json
from app.ml.chunking import chunk_text
from app.ml.pipeline import run_pipeline

router = APIRouter()

def validate_case(case_id: int, user_id: int, db: Session) -> CaseModel:
    case = db.query(CaseModel).filter(
        CaseModel.id == case_id,
        CaseModel.user_id == user_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    return case

@router.post("/cases/{case_id}/documents")
async def upload_documents(
    case_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"[UPLOAD] case_id={case_id}, user_id={current_user.id}, files_in_request={len(files)}")
    case = validate_case(case_id, current_user.id, db)

    if len(case.documents) + len(files) > 100:
        raise HTTPException(status_code=400, detail="Превышен лимит документов (100)")

    paths = storage_paths(case_id)
    for p in [paths["docs"], paths["chunks"], paths["state_dir"]]:
        p.mkdir(parents=True, exist_ok=True)

    processed = 0
    for file in files:
        try:
            content = await file.read()
            text = extract_text(file, content)
            cleaned = clean_text(text)
            tok_count = count_tokens(cleaned)
            logger.info(f"[UPLOAD] file='{file.filename}', type='{file.content_type}', len={len(cleaned)}, tokens={tok_count}")

            doc = DocumentModel(
                title=file.filename,
                filetype=file.content_type or "text/plain",
                created_at=datetime.now(timezone.utc),
                case_id=case.id
            )
            db.add(doc)
            db.flush()

            # сохраняем .txt
            (paths["docs"] / f"{doc.id}_{file.filename}.txt").write_text(cleaned, encoding="utf-8")

            # чанки -> .jsonl
            chunks = chunk_text(cleaned)
            with (paths["chunks"] / f"{doc.id}.jsonl").open("w", encoding="utf-8") as f:
                for ch in chunks:
                    rec = {"doc_id": str(doc.id), "title": file.filename, **ch}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            processed += 1
        except Exception as e:
            logger.exception(f"[UPLOAD] error '{file.filename}': {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка обработки {file.filename}: {e}")

    try:
        db.commit()
    except Exception as e:
        logger.exception(f"[UPLOAD] DB commit error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка сохранения в БД")

    return {"message": f"Загружено и проиндексировано {processed} документов"}

@router.get("/cases/{case_id}/prompt")
async def generate_and_analyze_prompt(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"[RUN] start: case_id={case_id}, user_id={current_user.id}")
    validate_case(case_id, current_user.id, db)
    res = await run_pipeline(case_id)
    return res
