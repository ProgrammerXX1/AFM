from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer
from app.core.weaviate_client import initialize_weaviate
from app.routes import auth, cases, ml
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import uvicorn
import os
import logging
import warnings

# 🔧 Загрузка переменных из .env
load_dotenv()

# ⚠️ Отключаем ворнинги от protobuf
warnings.filterwarnings("ignore", message="Protobuf gencode version .* is exactly one major version older.*")

# 🔍 Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 🌐 FastAPI App с Lifecycle
app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔄 Инициализация приложения...")
    initialize_weaviate()
    yield
    logger.info("🛑 Завершение работы приложения...")

# 🔒 Авторизация
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# 📦 Подключаем роуты
app.include_router(auth.router, tags=["Auth"])
app.include_router(cases.router, tags=["Cases"])
app.include_router(ml.router, tags=["ML"])

# 🌍 CORS из .env
cors_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Swagger с авторизацией
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

# 🚀 Запуск
if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "localhost")
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=False)
