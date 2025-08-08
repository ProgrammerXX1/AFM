from datetime import datetime
from app.core.weaviate_client import client, ensure_connection
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlalchemy.orm import Session, load_only
from typing import List
from pydantic import BaseModel
from app.models.cases import CaseModel, DocumentModel
from app.schemas.cases import CaseCreate, CaseOut, CaseShort, CaseDocumentPreview, DocumentOut, DocumentUpdate
from app.db.database import get_db
from app.security.security import get_current_user
from app.ml.Embed.pipeline import clear_seen_chunks  # обновим ниже
from app.models.user import User

import logging
logger = logging.getLogger(__name__)
router = APIRouter()
from weaviate.classes.query import Filter
@router.get("/cases/first/documents", response_model=List[CaseDocumentPreview], tags=["Cases"])
def get_first_case_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    first_case = db.query(CaseModel).filter(
        CaseModel.user_id == current_user.id
    ).order_by(CaseModel.id.asc()).first()

    if not first_case:
        raise HTTPException(status_code=404, detail="У вас пока нет дел")

    # Формируем список документов с добавлением case_number
    result = [
        CaseDocumentPreview(
            case_number=first_case.case_number,
            title=doc.title,
            created_at=doc.created_at
        )
        for doc in first_case.documents
    ]

    return result
@router.get("/cases/short", response_model=List[CaseShort], tags=["Cases"])
def get_short_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cases = db.query(CaseModel).filter(CaseModel.user_id == current_user.id).options(
        load_only(CaseModel.id, CaseModel.case_number, CaseModel.registration_date)
    ).all()
    return cases

@router.get("/cases/{case_id}", response_model=CaseOut, tags=["Cases"])
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    case = db.query(CaseModel).filter(
        CaseModel.id == case_id,
        CaseModel.user_id == current_user.id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    return case

@router.post("/cases", response_model=CaseOut, tags=["Cases"])
def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = CaseModel(
        user_id=current_user.id,
        case_number=case_data.case_number,
        surname=case_data.surname,
        name=case_data.name,
        patronymic=case_data.patronymic,
        iin=case_data.iin,
        organization=case_data.organization,
        investigator=case_data.investigator,
        registration_date=case_data.registration_date,
        qualification=case_data.qualification,
        damage_amount=case_data.damage_amount,
        income_amount=case_data.income_amount,
        qualification_date=case_data.qualification_date,
        indictment_date=case_data.indictment_date,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 🔍 Получаем документ и проверяем владельца
    document = db.query(DocumentModel).join(CaseModel).filter(
        DocumentModel.id == document_id,
        CaseModel.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # 🧹 Удаление чанков из Weaviate
    try:
        ensure_connection()

        collection = client.collections.get("Document")
        where_filter = (
            Filter.by_property("document_id").equal(document.id) &
            Filter.by_property("user_id").equal(current_user.id)
        )

        delete_result = collection.data.delete_many(where=where_filter)

        if delete_result and delete_result.matches > 0:
            logger.info(f"🗑️ Удалено чанков Weaviate: {delete_result.matches}")
        else:
            logger.warning("⚠️ delete_many ничего не удалил. Пробуем вручную...")

            objects = collection.query.fetch_objects(limit=1000, with_vector=False)
            to_delete = [
                obj for obj in objects.objects
                if obj.properties.get("document_id") == document.id and obj.properties.get("user_id") == current_user.id
            ]

            for obj in to_delete:
                try:
                    collection.data.delete_by_id(obj.uuid)
                    logger.info(f"✅ Удалён чанк UUID={obj.uuid}")
                except Exception as e:
                    logger.error(f"❌ Ошибка удаления UUID={obj.uuid}: {e}")

    except Exception as e:
        logger.warning(f"⚠️ Ошибка удаления чанков из Weaviate: {e}")

    # 🧽 Удаление связанных хэшей из TXT-файла
    try:
        clear_seen_chunks(
            user_id=current_user.id,
            case_id=document.case_id,
            document_id=document.id  # только эти три параметра
        )
    except Exception as e:
        logger.warning(f"⚠️ Ошибка очистки TXT-кэша чанков: {e}")

    # 🗑️ Удаление из базы данных
    db.delete(document)
    db.commit()

    return {"message": "Документ и его чанки удалены"}


@router.put("/documents/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: int,
    data: DocumentUpdate,  # вот здесь ключ!
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print(f"📩 [BACKEND] Тело запроса: {data}")  # FastAPI уже сам валидировал

    document = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.case.has(user_id=current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    document.title = data.title
    document.filetype = data.filetype
    db.commit()
    db.refresh(document)

    return document

