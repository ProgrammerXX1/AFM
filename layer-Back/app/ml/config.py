# -*- coding: utf-8 -*-
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Логгер (общий для пакета)
logger = logging.getLogger("app.ml")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ENV
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "deepseek-6.7b")
GENERATOR_URL = os.getenv("GENERATOR_URL")
if not GENERATOR_URL:
    raise RuntimeError("GENERATOR_URL не задан в .env")

MODEL_ENCODING = "cl100k_base"

# Storage
STORAGE_DIR = Path("storage/docs")

# Лимиты/бюджеты
MAX_MODEL_LEN = 32768
SYSTEM_BUDGET = 800
BATCH_MAX_FILES = 6
BATCH_MAX_TOKENS = 11000
CHUNK_TOKENS = 1800
CHUNK_OVERLAP = 200
PER_DOC_TOKEN_CAP = 2600
EXTRACT_MAX_TOKENS = 1200

# «УСТАНОВИЛ»
FINAL_MAX_TOKENS = int(os.getenv("FINAL_MAX_TOKENS", "3200"))
UST_MIN_PARAGRAPHS = int(os.getenv("UST_MIN_PARAGRAPHS", "8"))
UST_MIN_DOCREFS = int(os.getenv("UST_MIN_DOCREFS", "5"))
UST_MIN_WORDS = int(os.getenv("UST_MIN_WORDS", "650"))
UST_MAX_REFINE_ROUNDS = int(os.getenv("UST_MAX_REFINE_ROUNDS", "3"))
SUBTITLE_TEXT = "о квалификации уголовного правонарушения"
OFFENSE_DEFAULT_ARTICLE = "ст.217 ч.2 п.1 УК РК"

# Флаги пайплайна
SECTIONAL_EXTRACTION = True
ENABLE_PASS2_ON_GAPS = True
PASS2_PER_DOC_CAP = 2200
MARKER_SCAN_CHUNKS = 4
STATE_SNIPPET_SIZES = {"investigators": 4, "prosecutors": 4, "actors": 20, "victims": 30, "pyramid_indicators": 12}
UST_STATE_CAPS = {"actors": 60, "victims": 300, "events": 260, "money_flows": 180, "pyramid_indicators": 40, "mechanism_bullets": 25, "offense_articles": 8}

# Проверка покрытий по потерпевшим
VICTIM_PAR_MIN_DOCREFS = 1
VICTIM_PAR_MIN_KEYPOINTS = 3
