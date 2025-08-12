# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import asyncio
import random
from typing import Optional

import httpx
from httpx import HTTPStatusError, TransportError, TimeoutException

from .config import GENERATOR_MODEL, GENERATOR_URL, logger

# Базовые параметры генерации
_DEFAULT_TEMP = 0.1
_DEFAULT_TOP_P = 0.9
_DEFAULT_REPEAT_PENALTY = 1.05

# Мягкие стоп-секвенсы для JSON/текста
_DEFAULT_STOPS = ["```", "```json", "```python"]

# Запрещённые фразы (любой регистр/язык)
_BANNED_PATTERNS = re.compile(
    r"(извин|я\s+не\s+мог[уы]|не\s+могу|не\s+в\s+состоянии|как\s+(?:модель|ИИ|искусств\w+\s+интеллект)|"
    r"я\s+не\s+смогу|к\s+сожалению|не\s+удалось|привет[,! ]|hello[,! ]|hi[,! ])",
    re.IGNORECASE
)

async def call_generator(prompt: str, n_predict: int):
    """
    Низкоуровневый вызов модели (vLLM/OpenAI-совместимый endpoint).
    """
    payload = {
        "model": GENERATOR_MODEL,
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": _DEFAULT_TEMP,
        "top_p": _DEFAULT_TOP_P,
        "repeat_penalty": _DEFAULT_REPEAT_PENALTY,
        "stream": False,
        "stop": _DEFAULT_STOPS,
    }
    async with httpx.AsyncClient(timeout=240.0) as client:
        r = await client.post(GENERATOR_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        # разные провайдеры возвращают разный ключ
        return data.get("content") or data.get("response") or data.get("text", "") or ""

async def _try_once(label: str, prompt: str, n_predict: int, retries: int = 3) -> str:
    delay = 1.0
    for attempt in range(retries):
        try:
            logger.info(f"[GEN] {label} try#{attempt+1}, n_predict={n_predict}")
            return await call_generator(prompt, n_predict=n_predict)
        except HTTPStatusError as e:
            code = e.response.status_code
            logger.warning(f"[GEN] {label} HTTP {code} on n_predict={n_predict} (attempt {attempt+1}/{retries})")
            if 500 <= code < 600:
                await asyncio.sleep(delay + random.random()*0.3)
                delay = min(delay*1.6, 5.0)
                continue
            raise
        except (TransportError, TimeoutException) as e:
            logger.warning(f"[GEN] {label} transport error: {e} (attempt {attempt+1}/{retries})")
            await asyncio.sleep(delay + random.random()*0.3)
            delay = min(delay*1.6, 5.0)
    raise TimeoutException(f"Генератор не ответил после {retries} попыток (n_predict={n_predict})")

def _inject_guardrails(prompt: str) -> str:
    """
    К каждому промпту аккуратно добавляем короткий блок-запрет,
    чтобы модель не уводило в «извините/я не могу/как модель…».
    """
    guard = (
        "\n\n=== ЗАПРЕТЫ/ТОН ===\n"
        "Никогда не писать фразы вида: «извин», «не могу», «как модель/ИИ/ассистент», "
        "«недостаточно данных». Даже при неполноте фактов — формируй ответ из доступных сведений; "
        "разрешено использовать нейтральную формулу «по материалам дела установлено следующее». "
        "Никаких приветствий/болтовни/метакомментариев."
    )
    # чтобы не раздувать контекст для JSON-экстракции, если уже явно прописано — не добавляем второй раз
    if "ЗАПРЕТЫ/ТОН" in prompt or "Жёстко запрещены" in prompt or "Строго запрещены" in prompt:
        return prompt
    return prompt + guard

def _has_banned(text: str) -> bool:
    return bool(_BANNED_PATTERNS.search(text or ""))

async def _rewrite_without_banned(text: str, label: str) -> str:
    """
    Если модель всё же выдала запрещённые фразы — мягко перегенерим «перепиши без…».
    """
    rewrite_prompt = (
        "Перепиши следующий текст тем же языком и стилем, убрав все фразы вида "
        "«извин», «не могу», «как модель/ИИ/ассистент», «недостаточно данных», «привет» и любые приветствия. "
        "Ничего не добавляй от себя, только переформулируй/удали запрещённые фрагменты. Верни ТОЛЬКО очищенный текст.\n\n"
        "Текст:\n" + text
    )
    try:
        cleaned = await _try_once(label + " REWRITE", rewrite_prompt, n_predict=min(1200, max(400, len(text)//2)))
        return cleaned or text
    except Exception as e:
        logger.warning(f"[GEN] {label} rewrite failed -> {e}; fallback to regex-strip")
        # Фолбэк: выпилим строки с «извин/не могу/как модель/привет»
        lines = []
        for ln in (text or "").splitlines():
            if _has_banned(ln):
                continue
            lines.append(ln)
        return "\n".join(lines).strip()

async def safe_call_generator(
    prompt: str,
    n_predict: int,
    label: str = "",
    retries: int = 3,
    fallback_predict: Optional[list[int]] = None,
    inject_guard: bool = True
) -> str:
    """
    Безопасный вызов генератора:
      1) ретраи при сетевых/5xx;
      2) фолбэки по длине ответа;
      3) опциональная инъекция «guardrails» (запрет извинений/отказов);
      4) пост-фильтр: если появились запрещённые фразы — переписать.
    """
    pp = _inject_guardrails(prompt) if inject_guard else prompt

    # 1) основной размер
    try:
        out = await _try_once(label, pp, n_predict, retries=retries)
    except Exception:
        out = None

    # 2) фолбэки по длине при неудаче
    if out is None:
        fb = fallback_predict or [2400, 2000, 1600, 1200, 800]
        for np in fb:
            try:
                logger.info(f"[GEN] {label} fallback n_predict={np}")
                out = await _try_once(label, pp, np, retries=retries)
                break
            except Exception:
                continue
        if out is None:
            raise TimeoutException("Генератор недоступен даже с укороченными ответами")

    # 3) пост-фильтр на запрещённые фразы
    if _has_banned(out):
        logger.info(f"[GEN] {label}: banned phrases detected, rewriting")
        out = await _rewrite_without_banned(out, label)

    return out or ""
