from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class CaseModel(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_number = Column(String, unique=True, index=True, nullable=False)

    # 🔗 связь с пользователем
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="cases")

    # [Личные данные]
    surname = Column(String, nullable=False)
    name = Column(String, nullable=False)
    patronymic = Column(String)
    iin = Column(String, nullable=False, unique=True)

    # [Сведения по делу]
    organization = Column(String)
    investigator = Column(String)
    registration_date = Column(Date)
    qualification = Column(String)
    damage_amount = Column(Float)
    income_amount = Column(Float)
    qualification_date = Column(Date)
    indictment_date = Column(Date)

    # [Документы]
    documents = relationship("DocumentModel", back_populates="case", cascade="all, delete-orphan")
    

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    weaviate_id = Column(String, nullable=False)
    title = Column(String)
    filetype = Column(String)
    created_at = Column(Date, default=datetime.utcnow)

    case = relationship("CaseModel", back_populates="documents")
