# app/routes/plan.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.security.security import get_current_user
from app.models.user import User
from app.models.cases import CaseModel
from app.ml.embedding_pipeline import search_similar_chunks

router = APIRouter()

@router.get("/cases/{case_id}/search")
async def search_documents(
    case_id: int,
    question: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(CaseModel).filter(
        CaseModel.id == case_id,
        CaseModel.user_id == current_user.id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")

    try:
        results = search_similar_chunks(question=question, case_id=case_id, k=5)
        return {"results": results}
    except Exception as e:
        print(f"❌ Ошибка поиска: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")