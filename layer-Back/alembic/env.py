import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from dotenv import load_dotenv
load_dotenv()  # ⬅️ Загружаем переменные из .env

# Alembic Config object
config = context.config

# Настройка логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Получаем URL базы данных из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ Переменная DATABASE_URL не найдена в .env")

# Устанавливаем URL в конфигурацию Alembic
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# 📦 Импорт всех моделей для автогенерации миграций
from app.db.database import Base
from app.models.cases import CaseModel, DocumentModel
from app.models.user import User

# Метаинформация для Alembic
target_metadata = Base.metadata

# =============================
# 🔧 OFFLINE MIGRATIONS
# =============================
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# =============================
# 🔧 ONLINE MIGRATIONS
# =============================
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

# =============================
# 🚀 ВЫЗОВ
# =============================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
