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
# --- ADD near imports ---
from typing import Any, Dict
# --- END ADD ---

def _extract_text(data: Dict[str, Any]) -> str:
    """
    Унифицируем разные форматы ответов:
    - OpenAI chat: choices[0].message.content
    - OpenAI completions: choices[0].text
    - кастом/llama.cpp: content / response / text
    """
    if not isinstance(data, dict):
        return ""
    # OpenAI chat
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        pass
    # OpenAI completions
    try:
        return data["choices"][0]["text"]
    except Exception:
        pass
    # Кастомные ключи
    return data.get("content") or data.get("response") or data.get("text", "") or ""

async def call_generator(prompt: str, n_predict: int):
    """
    Умный вызов генератора: поддержка OpenAI /v1/chat/completions,
/v1/completions и llama.cpp-подобных серверов.
    Сначала пытаемся «по URL», при 400 — пробуем другие схемы.
    """
    url = GENERATOR_URL

    # Схемы тел
    payload_chat = {
        "model": GENERATOR_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": n_predict,
        "temperature": _DEFAULT_TEMP,
        "top_p": _DEFAULT_TOP_P,
        "stream": False,
        "stop": _DEFAULT_STOPS,
    }
    payload_comp = {
        "model": GENERATOR_MODEL,
        "prompt": prompt,
        "max_tokens": n_predict,
        "temperature": _DEFAULT_TEMP,
        "top_p": _DEFAULT_TOP_P,
        "stream": False,
        "stop": _DEFAULT_STOPS,
    }
    payload_llama = {
        "model": GENERATOR_MODEL,
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": _DEFAULT_TEMP,
        "top_p": _DEFAULT_TOP_P,
        "repeat_penalty": _DEFAULT_REPEAT_PENALTY,
        "stream": False,
        "stop": _DEFAULT_STOPS,
    }

    # Порядок попыток по эвристике URL
    attempts = []
    u = (url or "").lower()
    if "/chat/completions" in u:
        attempts = [("openai-chat", payload_chat), ("openai-comp", payload_comp), ("llama", payload_llama)]
    elif "/completions" in u:
        attempts = [("openai-comp", payload_comp), ("openai-chat", payload_chat), ("llama", payload_llama)]
    else:
        attempts = [("llama", payload_llama), ("openai-chat", payload_chat), ("openai-comp", payload_comp)]

    async with httpx.AsyncClient(timeout=240.0) as client:
        last_exc: Optional[Exception] = None
        for label, pl in attempts:
            try:
                r = await client.post(url, json=pl)
                r.raise_for_status()
                data = r.json()
                return _extract_text(data)
            except HTTPStatusError as e:
                # При явной 400 — пробуем следующую схему
                if e.response is not None and e.response.status_code == 400:
                    try:
                        err_txt = e.response.text[:500]
                    except Exception:
                        err_txt = str(e)
                    logger.warning(f"[GEN] {label} -> HTTP 400, retry with next schema; body: {err_txt}")
                    last_exc = e
                    continue
                last_exc = e
                break
            except Exception as e:
                logger.warning(f"[GEN] transport/parse error on {label}: {e}")
                last_exc = e
                continue

        # Если всё перепробовали
        if last_exc:
            raise last_exc
        raise RuntimeError("Generator: no attempts executed (invalid configuration)")

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
