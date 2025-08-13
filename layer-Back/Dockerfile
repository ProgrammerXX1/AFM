# ⚙️ Базовый образ
FROM python:3.11-slim

# 📍 Устанавливаем рабочую директорию
WORKDIR /app

# ✅ Копируем только файл зависимостей для установки
COPY requirements.txt .

# 🧱 Устанавливаем зависимости отдельно — будет кешироваться
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libffi-dev \
    libpq-dev \
    libmupdf-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y gcc build-essential \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ✅ Только теперь копируем оставшийся код (возможно изменяется часто)
COPY . .

# 🚀 Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
