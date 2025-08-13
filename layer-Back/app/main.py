# app/main.py
from __future__ import annotations

import os
import warnings
import logging
from datetime import date
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer
import uvicorn

from app.core.weaviate_client import (
    connect as weaviate_connect,
    ensure_schema as weaviate_ensure_schema,
    close_client as weaviate_close,
    is_connected as weaviate_is_connected,
)
from app.db.database import SessionLocal
from app.models.user import User
from app.models.cases import CaseModel
from app.security.security import get_password_hash
from app.routes import auth, cases, ml

# 🔧 env
load_dotenv()

# ⚠️ protobuf warning
warnings.filterwarnings("ignore", message="Protobuf gencode version .* is exactly one major version older.*")

# 🔍 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 🌐 FastAPI App (с lifespan сразу в конструкторе)
def bootstrap_default_user_and_case():
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username="beka").first()
        if not user:
            user = User(
                username="beka",
                hashed_password=get_password_hash("2123"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("👤 Создан юзер 'beka'")

        case = db.query(CaseModel).filter_by(case_number="CASE-001").first()
        if not case:
            case = CaseModel(
                case_number="CASE-001",
                user_id=user.id,
                surname="Исенов",
                name="Дастан",
                patronymic="Бекболатович",
                iin="990123456789",
                organization="ДЕРА Павлодар",
                investigator="Серик Закиев",
                registration_date=date(2025, 8, 1),
                qualification="ст. 217 ч.1 п.1 УК РК",
                damage_amount=2_300_000.50,
                income_amount=750_000.00,
                qualification_date=date(2025, 8, 2),
                indictment_date=date(2025, 8, 12),
            )
            db.add(case)
            db.commit()
            logger.info("📄 Создано дело 'CASE-001'")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔄 Инициализация приложения...")
    try:
        # 1) Weaviate up
        weaviate_connect()
        weaviate_ensure_schema()

        # 2) Bootstrap demo data
        bootstrap_default_user_and_case()

        yield
    finally:
        # Корректное закрытие при shutdown
        if weaviate_is_connected():
            weaviate_close()
        logger.info("🛑 Завершение работы приложения...")

app = FastAPI(lifespan=lifespan)

# 🔒 OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# 📆 Роуты
app.include_router(auth.router, tags=["Auth"])
app.include_router(cases.router, tags=["Cases"])
app.include_router(ml.router, tags=["ML"])

# 🌍 CORS
cors_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Swagger + Bearer Auth
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="AFM API",
        version="1.0.0",
        description="API for authentication and users",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"OAuth2PasswordBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", 8001))
    # Важно: lifespan должен быть включен (по умолчанию on). reload=False в проде — ок.
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
