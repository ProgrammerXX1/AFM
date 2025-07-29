from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer
from app.core.weaviate_client import initialize_weaviate
from contextlib import asynccontextmanager

import logging
import warnings

warnings.filterwarnings("ignore", message="Protobuf gencode version .* is exactly one major version older.*")
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)
app = FastAPI()
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, выполняемый при старте приложения
    logger.info("Инициализация приложения...")
    initialize_weaviate()
    yield
    # Код, выполняемый при завершении приложения
    logger.info("Завершение работы приложения...")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")  # важно

# Добавь роуты после инициализации приложения
from app.routes import auth, cases, ml
app.include_router(auth.router, tags=["Auth"])
app.include_router(cases.router, tags=["Cases"])
app.include_router(ml.router, tags=["ML"])
# Настройка CORS (опционально, если фронт подключаешь)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Swagger авторизация
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
