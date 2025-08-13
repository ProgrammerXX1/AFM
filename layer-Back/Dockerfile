# ⚙️ Базовый образ
FROM python:3.11-slim

# системные зависимости для psycopg2, cryptography, pymupdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libffi-dev libpq-dev libmupdf-dev wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# сначала зависимости (кешируется)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# теперь код
COPY . .

# на всякий — выставим PYTHONPATH
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 👇 ВАЖНО: если ваш main лежит в app/main.py — оставляем app.main:app
# если файл на корне layer-Back/main.py — меняйте на main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
