from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class CaseShort(BaseModel):
    id: int
    case_number: str
    registration_date: Optional[date]

    class Config:
        from_attributes = True  # ✅ Новый синтаксис


class DocumentOut(BaseModel):
    id: int
    title: str
    filetype: str
    weaviate_id: Optional[str]  # если есть
    created_at: date

    class Config:
        from_attributes = True  # ✅ Новый синтаксис


class CaseCreate(BaseModel):
    case_number: str
    surname: str
    name: str
    patronymic: Optional[str]
    iin: str
    organization: Optional[str]
    investigator: Optional[str]
    registration_date: Optional[date]
    qualification: Optional[str]
    damage_amount: Optional[float]
    income_amount: Optional[float]
    qualification_date: Optional[date]
    indictment_date: Optional[date]


class CaseOut(BaseModel):
    id: int
    case_number: str
    surname: str
    name: str
    patronymic: Optional[str]
    iin: str
    organization: Optional[str]
    investigator: Optional[str]
    registration_date: Optional[date]
    qualification: Optional[str]
    damage_amount: Optional[float]
    income_amount: Optional[float]
    qualification_date: Optional[date]
    indictment_date: Optional[date]
    documents: List[DocumentOut]

    class Config:
        from_attributes = True  # ✅ Новый синтаксис

class CaseDocumentPreview(BaseModel):
    case_number: str
    title: str
    created_at: date

    class Config:
        from_attributes = True  # ✅ Новый синтаксис

class DocumentUpdate(BaseModel):
    title: str
    filetype: str
    content: str  
