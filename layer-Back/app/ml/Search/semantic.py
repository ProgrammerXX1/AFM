from fastapi import APIRouter, HTTPException, Depends, Query
from app.ml.Embed.embedding_pipeline import search_similar_chunks
from app.models.user import User
from app.security.security import get_current_user

router = APIRouter()

@router.get("/cases/{case_id}/search")
async def semantic_search(
    case_id: int,
    q: str = Query(..., description="Ваш поисковый запрос"),
    current_user: User = Depends(get_current_user)
):
    try:
        results = search_similar_chunks(query=q, case_id=case_id, top_k=10)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))