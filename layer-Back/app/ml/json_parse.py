# app/ml/json_parse.py
# -*- coding: utf-8 -*-
"""
JSON-ремонт/парсинг + нормализация сущностей.
- parse_or_retry_json: получает ответ LLM и возвращает валидный dict.
- unify_victim_record / unify_victims_from_response: приводит потерпевших к единой схеме.
- extract_scenario_from_text: строит шаги сценария из текста протокола.
"""

from __future__ import annotations

import re
import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import logger
from .io_utils import count_tokens, storage_paths

# ---------- Markdown fences ----------
MD_FENCE_RE = re.compile(r"```(?:[a-zA-Z]+)?\s*([\s\S]*?)```", re.IGNORECASE)

# ---------- Денежные суммы/даты (рус.) ----------
MONEY_RE = re.compile(
    r"(?P<amount>(?:\d{1,3}(?:[\s\.]\d{3})+|\d+))(?:\s*(?:тенге|тг|KZT))?",
    re.IGNORECASE,
)
DATE_DDMMYYYY_RE = re.compile(r"\b(?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4})\b")

# ---------- Платформы / ключевые маркеры сценария ----------
PLATFORM_PATTERNS = [
    (re.compile(r"\bOKX\b", re.IGNORECASE), "OKX"),
    (re.compile(r"\bP2P\b", re.IGNORECASE), "P2P"),
    (re.compile(r"\bUSDT\b", re.IGNORECASE), "USDT"),
    (re.compile(r"\bKaspi\b", re.IGNORECASE), "KASPI"),
    (re.compile(r"\bTakorp\b", re.IGNORECASE), "TAKORP"),
]
SCENARIO_HINTS = {
    "invite": re.compile(r"реферал|реферальн|приглас|5\s*челов", re.IGNORECASE),
    "register": re.compile(r"зарегистр|реферал.*ссылк|получил.*ссылк", re.IGNORECASE),
    "okx_wallet": re.compile(r"OKX|кошел[её]к", re.IGNORECASE),
    "p2p_buy": re.compile(r"P2P|USDT|Kaspi|Касп[иы]", re.IGNORECASE),
    "deposit": re.compile(r"пополнил|перев[её]л.*кабинет|личн(ый|ом)\s+кабинет", re.IGNORECASE),
    "tasks": re.compile(r"задан(ие|ия)|бонус(ы)?|начислен", re.IGNORECASE),
    "withdraw_attempt": re.compile(r"вывод|блокиров|заблокир", re.IGNORECASE),
    "loss": re.compile(r"ущерб|в размере|сумма", re.IGNORECASE),
}

# ---------- Вспомогалки для JSON ремонта ----------
def pick_json_candidate(s: str) -> str:
    m = MD_FENCE_RE.search(s)
    return m.group(1).strip() if m else s

def balance_json_brackets(s: str) -> str:
    s = s.strip()
    first = s.find("{")
    if first > 0:
        s = s[first:]
    stack: List[str] = []
    out: List[str] = []
    in_str = False
    esc = False
    for ch in s:
        out.append(ch)
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack and ((stack[-1] == "{" and ch == "}") or (stack[-1] == "[" and ch == "]")):
                stack.pop()
    while stack:
        open_ch = stack.pop()
        out.append("}" if open_ch == "{" else "]")
    return "".join(out)

def json_repair_min(s: str) -> str:
    s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r"\b-?Infinity\b", "null", s)
    s = re.sub(r"\bNaN\b", "null", s)
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    s = re.sub(r",\s*([\]\}])", r"\1", s)
    s = re.sub(
        r'(?m)(?P<prefix>[\s\{,])([A-Za-z_][A-Za-z0-9_]*)\s*:',
        lambda m: m.group("prefix") + f'"{m.group(2)}":',
        s,
    )
    s = balance_json_brackets(s)
    return s

def extract_first_json_block(s: str) -> str:
    cand = pick_json_candidate(s)
    i = cand.find("{")
    if i == -1:
        raise ValueError("В ответе нет '{'")
    depth = 0
    in_str = False
    esc = False
    for j, ch in enumerate(cand[i:], start=i):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return cand[i : j + 1]
    return cand[i:]

def log_batch_raw(batch_id: str | int, label: str, text: str):
    logger.info(
        f"\n===== BATCH {batch_id} RAW {label} START =====\n{text}\n===== BATCH {batch_id} RAW {label} END =====\n"
    )

async def parse_or_retry_json(
    first_prompt: str,
    call_fn,
    n_predict: int,
    batch_id: str | int,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Главная точка входа: получить из LLM валидный JSON dict с ретраями/ремонтом."""
    prompt_tokens = count_tokens(first_prompt)
    logger.info(f"[EXTRACT] B{batch_id}: prompt_tokens={prompt_tokens}, n_predict={n_predict}")
    raw_first = await call_fn(first_prompt, n_predict=n_predict)
    log_batch_raw(batch_id, "FIRST", raw_first)

    try:
        blk = extract_first_json_block(raw_first)
        fixed = json_repair_min(blk)
        data = json.loads(fixed)
        logger.info(f"[EXTRACT] B{batch_id}: JSON parsed OK (FIRST)")
        return data
    except Exception as e:
        logger.info(f"[EXTRACT] B{batch_id}: FIRST parse failed -> {e}")

    delay = 1.0
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            repair_prompt = (
                "Сделай из следующего ответа СТРОГО ВАЛИДНЫЙ JSON по заданной схеме. "
                "Верни ТОЛЬКО JSON, без лишнего текста и без markdown.\n\nОтвет:\n" + raw_first
            )
            logger.info(f"[EXTRACT] B{batch_id}: RETRY#{attempt+1} prompt_tokens={count_tokens(repair_prompt)}")
            raw_retry = await call_fn(repair_prompt, n_predict=min(600, n_predict))
            log_batch_raw(batch_id, f"RETRY#{attempt+1}", raw_retry)
            blk = extract_first_json_block(raw_retry)
            fixed = json_repair_min(blk)
            data = json.loads(fixed)
            logger.info(f"[EXTRACT] B{batch_id}: JSON parsed OK (RETRY#{attempt+1})")
            return data
        except (httpx.HTTPError, httpx.TransportError) as e:
            last_err = e
            logger.info(f"[EXTRACT] B{batch_id}: transport error on RETRY#{attempt+1} -> {e}, sleep {delay}s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 4.0)
        except Exception as e:
            last_err = e
            logger.info(f"[EXTRACT] B{batch_id}: parse error on RETRY#{attempt+1} -> {e}, sleep {delay}s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 4.0)

    # salvage из первого ответа
    try:
        blk = extract_first_json_block(raw_first)
    except Exception:
        blk = raw_first
    fixed = json_repair_min(blk)
    try:
        data = json.loads(fixed)
        logger.info(f"[EXTRACT] B{batch_id}: JSON parsed OK (SALVAGE)")
        return data
    except Exception as e:
        dbg_path = storage_paths(0)["state_dir"] / f"batch_{str(batch_id)}_raw_final_fail.txt"
        dbg_path.parent.mkdir(parents=True, exist_ok=True)
        dbg_path.write_text(raw_first, encoding="utf-8")
        logger.error(f"[EXTRACT] B{batch_id}: JSON final fail -> saved to {dbg_path}")
        raise e if last_err is None else last_err


# ===================================================================
# ----------------------- НОРМАЛИЗАЦИЯ VICTIM -----------------------
# ===================================================================

def _to_int_safe(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, (int, float)):
        return int(x)
    s = str(x)
    m = MONEY_RE.search(s)
    if m:
        amt = m.group("amount").replace(" ", "").replace(".", "")
        try:
            return int(amt)
        except Exception:
            pass
    # «чистка» всех нецифр:
    digits = re.sub(r"\D+", "", s)
    try:
        return int(digits) if digits else 0
    except Exception:
        return 0

def _to_str_or_none(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s or None

def _coerce_doc_refs(refs: Any) -> List[str]:
    out: List[str] = []
    if isinstance(refs, str):
        out = [refs]
    elif isinstance(refs, list):
        out = [str(r).strip() for r in refs if r]
    return list(dict.fromkeys([r for r in out if r]))  # uniq & non-empty

def _parse_date(s: Any) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    m = DATE_DDMMYYYY_RE.search(s)
    if m:
        return f"{m.group('d')}.{m.group('m')}.{m.group('y')}"
    # допускаем ISO -> DD.MM.YYYY
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            y, m, d = s.split("-")
            return f"{d}.{m}.{y}"
    except Exception:
        pass
    return None

def _platforms_from_text(text: Optional[str]) -> List[Dict[str, Optional[str]]]:
    acc: List[Dict[str, Optional[str]]] = []
    if not text:
        return acc
    seen = set()
    for rx, name in PLATFORM_PATTERNS:
        if rx.search(text):
            if name not in seen:
                seen.add(name)
                acc.append({"service": name, "id": None})
    return acc

def extract_scenario_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Грубая реконструкция шагов сценария по ключевым словам.
    Возвращает steps = [{"order": n, "date": None|str, "action": "...", "details": "...", "doc_refs": []}, ...]
    """
    if not text:
        return []

    steps: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def add_step(tag: str, action: str, detail: Optional[str] = None):
        if tag in seen:
            return
        seen.add(tag)
        steps.append({
            "order": len(steps) + 1,
            "date": None,  # можно попытаться поднять ближайшую дату:
            "action": action,
            "details": (detail or "")[:300],
            "doc_refs": [],
        })

    # порядок как в требовании
    if SCENARIO_HINTS["register"].search(text):
        add_step("register", "Получил реферальную ссылку и зарегистрировался", None)

    if SCENARIO_HINTS["okx_wallet"].search(text):
        add_step("okx_wallet", "Создал кошелёк/аккаунт в OKX", None)

    if SCENARIO_HINTS["p2p_buy"].search(text):
        add_step("p2p_buy", "Купил USDT через P2P (например, Kaspi)", None)

    if SCENARIO_HINTS["deposit"].search(text):
        add_step("deposit", "Пополнил «кабинет» на платформе", None)

    if SCENARIO_HINTS["tasks"].search(text):
        add_step("tasks", "Выполнял задания / получал бонусы", None)

    if SCENARIO_HINTS["invite"].search(text):
        add_step("invite", "Получал/выплачивал реферальные бонусы, требование ≥5 приглашений", None)

    if SCENARIO_HINTS["withdraw_attempt"].search(text):
        add_step("withdraw_attempt", "Предпринимал попытку вывода, столкнулся с блокировкой", None)

    if SCENARIO_HINTS["loss"].search(text):
        # Попытка вытащить сумму
        dmg = None
        m = MONEY_RE.search(text)
        if m:
            amt = m.group("amount").replace(" ", "").replace(".", "")
            try:
                dmg = int(amt)
            except Exception:
                dmg = None
        detail = f"Итоговый ущерб зафиксирован{f' — {dmg} тг' if dmg else ''}"
        add_step("loss", "Зафиксирован ущерб", detail)

    return steps


def unify_victim_record(
    raw: Dict[str, Any],
    default_doc_ref: Optional[str] = None,
    source_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Приводит «потерпевшего» к унифицированной схеме:
    {
      "name": "...", "dob": "DD.MM.YYYY", "address": "...",
      "phone": "...", "damage_tenge": 0,
      "doc_refs": ["doc:..#chunk:.."],
      "steps": [{"order":1,"action":"...","date":null,"details":"...","doc_refs":[]}],
      "platform_accounts":[{"service":"OKX","id":null}]
    }
    """
    v: Dict[str, Any] = {}
    v["name"] = _to_str_or_none(raw.get("name"))
    v["dob"] = _parse_date(raw.get("dob"))
    v["address"] = _to_str_or_none(raw.get("address"))
    v["phone"] = _to_str_or_none(raw.get("phone"))
    v["damage_tenge"] = _to_int_safe(raw.get("damage_tenge") or raw.get("damage") or raw.get("loss"))

    # ссылки
    refs = _coerce_doc_refs(raw.get("doc_refs"))
    if default_doc_ref and default_doc_ref not in refs:
        refs.append(default_doc_ref)
    v["doc_refs"] = refs

    # steps
    steps_in = raw.get("steps") if isinstance(raw.get("steps"), list) else []
    steps_norm: List[Dict[str, Any]] = []
    for i, st in enumerate(steps_in, start=1):
        if not isinstance(st, dict):
            continue
        steps_norm.append({
            "order": int(st.get("order") or i),
            "date": _parse_date(st.get("date")),
            "action": _to_str_or_none(st.get("action")) or "",
            "details": _to_str_or_none(st.get("details")) or "",
            "doc_refs": _coerce_doc_refs(st.get("doc_refs")),
        })

    # если шагов нет — попробуем собрать из текста протокола
    if not steps_norm and source_text:
        steps_norm = extract_scenario_from_text(source_text)

    v["steps"] = steps_norm

    # platform_accounts
    plats_in = raw.get("platform_accounts") if isinstance(raw.get("platform_accounts"), list) else []
    plats_norm: List[Dict[str, Optional[str]]] = []
    for p in plats_in:
        if not isinstance(p, dict):
            continue
        service = _to_str_or_none(p.get("service"))
        pid = _to_str_or_none(p.get("id"))
        if service:
            plats_norm.append({"service": service, "id": pid})

    # добавим по тексту
    for p in _platforms_from_text(source_text or ""):
        if all(pp.get("service") != p["service"] for pp in plats_norm):
            plats_norm.append(p)

    v["platform_accounts"] = plats_norm

    # гарантированные поля
    for k in ("name", "dob", "address", "phone"):
        if k not in v:
            v[k] = None
    if "damage_tenge" not in v:
        v["damage_tenge"] = 0
    if "doc_refs" not in v:
        v["doc_refs"] = []
    if "steps" not in v:
        v["steps"] = []
    if "platform_accounts" not in v:
        v["platform_accounts"] = []

    return v


def unify_victims_from_response(
    data: Dict[str, Any],
    default_doc_ref: Optional[str] = None,
    source_text_by_ref: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Пройдётся по возможным путям с потерпевшими в ответе LLM и вернёт унифицированный список.
    - data["victims_add"] (новая секционная схема)
    - data["victims"] (если кто-то вернул без _add)
    - data["actors_add"] с role~"потерпевший" (на крайний случай)
    """
    victims: List[Dict[str, Any]] = []

    def _source_text_for(v: Dict[str, Any]) -> Optional[str]:
        if not source_text_by_ref:
            return None
        for r in v.get("doc_refs", []) or []:
            if r in source_text_by_ref:
                return source_text_by_ref[r]
        return None

    # 1) victims_add
    if isinstance(data.get("victims_add"), list):
        for raw in data["victims_add"]:
            if isinstance(raw, dict):
                refs = _coerce_doc_refs(raw.get("doc_refs"))
                src_text = _source_text_for({"doc_refs": refs})
                victims.append(unify_victim_record(raw, default_doc_ref=default_doc_ref, source_text=src_text))

    # 2) victims
    elif isinstance(data.get("victims"), list):
        for raw in data["victims"]:
            if isinstance(raw, dict):
                refs = _coerce_doc_refs(raw.get("doc_refs"))
                src_text = _source_text_for({"doc_refs": refs})
                victims.append(unify_victim_record(raw, default_doc_ref=default_doc_ref, source_text=src_text))

    # 3) actors_add с ролью «потерпевший»
    if isinstance(data.get("actors_add"), list):
        for a in data["actors_add"]:
            if not isinstance(a, dict):
                continue
            roles = a.get("role") if isinstance(a.get("role"), list) else [a.get("role")]
            roles = [str(r).lower() for r in roles if r]
            if any("потерп" in r for r in roles):
                raw = {
                    "name": a.get("name"),
                    "doc_refs": a.get("doc_refs"),
                    "damage_tenge": a.get("damage_tenge"),
                }
                refs = _coerce_doc_refs(raw.get("doc_refs"))
                src_text = _source_text_for({"doc_refs": refs})
                victims.append(unify_victim_record(raw, default_doc_ref=default_doc_ref, source_text=src_text))

    return victims


__all__ = [
    "parse_or_retry_json",
    "extract_first_json_block",
    "json_repair_min",
    "extract_scenario_from_text",
    "unify_victim_record",
    "unify_victims_from_response",
]
