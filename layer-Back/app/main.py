from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import logging
import warnings
from pathlib import Path

# ⬇️ DB/Alembic
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import Base, engine, SessionLocal
from alembic import command
from alembic.config import Config

# ⬇️ Модели (если у тебя другие пути — поправь)
from app.models.user import User
from app.models.case import CaseModel

# ⬇️ Пароли для сидинга
from passlib.context import CryptContext
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ⬇️ Остальное
from app.core.weaviate_client import initialize_weaviate
from app.routes import auth, cases, ml
from datetime import date

# 🔧 Загрузка .env
load_dotenv()

# ⚠️ Тишим protobuf
warnings.filterwarnings("ignore", message="Protobuf gencode version .* is exactly one major version older.*")

# 🔍 Логи
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------- Миграции и сидинг ---------

def run_migrations_or_create():
    """Сначала пытаемся прогнать Alembic, если не вышло — create_all."""
    db_url = os.getenv("DATABASE_URL")
    # проверим коннект
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ DB connection OK")
    except SQLAlchemyError as e:
        logger.exception("❌ DB connection failed")
        raise

    # конфиг Alembic
    # ожидаем, что /app — корень проекта в контейнере
    project_root = Path(__file__).resolve().parents[1]
    alembic_ini = project_root / "alembic.ini"
    alembic_dir = project_root / "alembic"

    try:
        cfg = Config(str(alembic_ini)) if alembic_ini.exists() else Config()
        cfg.set_main_option("script_location", str(alembic_dir))
        if db_url:
            cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(cfg, "head")
        logger.info("✅ Alembic migrations applied (head)")
    except Exception as e:
        logger.warning(f"⚠️ Alembic failed ({e}). Fallback to Base.metadata.create_all()")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created via SQLAlchemy")

def seed_minimal_data():
    """Гарантируем 1 пользователя и 2 дела у него (идемпотентно)."""
    admin_username = os.getenv("SEED_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "admin")

    with SessionLocal() as db:
        # пользователь
        user = db.query(User).filter(User.username == admin_username).first()
        if not user:
            user = User(
                username=admin_username,
                hashed_password=pwd_ctx.hash(admin_password),
            )
            db.add(user)
            db.flush()  # получим user.id без отдельного коммита
            logger.info("👤 Seed: created user 'admin'")
        else:
            logger.info("👤 Seed: user 'admin' already exists")

        # дела (минимально обязательные поля из твоей модели)
        def ensure_case(case_number: str, iin: str):
            exists = db.query(CaseModel).filter(CaseModel.case_number == case_number).first()
            if exists:
                return
            c = CaseModel(
                case_number=case_number,
                user_id=user.id,
                surname="Иванов",
                name="Иван",
                patronymic="Иванович",
                iin=iin,
                organization=None,
                investigator=None,
                registration_date=date.today(),
                qualification=None,
                damage_amount=None,
                income_amount=None,
                qualification_date=None,
                indictment_date=None,
            )
            db.add(c)
            logger.info(f"📄 Seed: created case {case_number}")

        ensure_case("CASE-0001", "000000000000")
        ensure_case("CASE-0002", "000000000001")
        db.commit()
        logger.info("✅ Seed committed")

# --------- FastAPI app ---------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔄 App init: running migrations & seed...")
    run_migrations_or_create()
    seed_minimal_data()
    logger.info("🔄 App init: initializing Weaviate...")
    initialize_weaviate()
    yield
    logger.info("🛑 App shutdown")

# ВАЖНО: реально используем lifespan
app = FastAPI(lifespan=lifespan)

# 🔒 Авторизация
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# 📦 Роуты
app.include_router(auth.router, tags=["Auth"])
app.include_router(cases.router, tags=["Cases"])
app.include_router(ml.router, tags=["ML"])

# 🌍 CORS
cors_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Swagger c bearer
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

# 🚀 Локальный запуск (в докере ты стартуешь uvicorn через CMD)
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
