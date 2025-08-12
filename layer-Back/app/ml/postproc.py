# -*- coding: utf-8 -*-
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from .config import logger
from .io_utils import count_words

RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def format_kz_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str)
        return f"{dt.day} {RU_MONTHS.get(dt.month, '')} {dt.year} года"
    except Exception:
        m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", date_str)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{d} {RU_MONTHS.get(mo, '')} {y} года"
        return date_str

def collapse_repeated_lines(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    seen = set()
    out = []
    for ln in lines:
        key = ln.strip().lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(ln)
    return "\n".join(out)

GENERIC_FILLER_PATTS = [
    r"^В ходе расследования были обнаружены другие факты.*$",
    r"^В ходе расследования было принято решение.*$",
    r"^В ходе этого расследования.*$",
    r"^В данном случае не было найдено информации.*$",
    r"^Во-первых, необходимо отметить, что данные не содержат.*$",
    r"^Во-вторых, необходимо отметить, что данные не содержат.*$",
    r"^В-третьих, необходимо отметить, что данные не содержат.*$",
]
def drop_generic_filler(text: str) -> str:
    out_lines = []
    for ln in text.splitlines():
        if any(re.match(p, ln.strip(), flags=re.IGNORECASE) for p in GENERIC_FILLER_PATTS):
            continue
        out_lines.append(ln)
    s = "\n".join(out_lines)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s

ERDR_NUM_RE = re.compile(r"(?:№\s*)(\d{8,20})")
def normalize_erdr_mentions(text: str, erdr: Optional[str]) -> str:
    if not erdr:
        return text
    return ERDR_NUM_RE.sub(lambda m: f"№{erdr}", text)

DOCREF_RE = re.compile(r"\(см\.\s*doc:\d+#chunk:\d+\)", re.IGNORECASE)
def paragraphs(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

def ensure_minimum_evidence(text: str,
                            min_paragraphs: int,
                            min_docrefs: int,
                            min_words: int) -> Tuple[bool, int, int, int]:
    pars = paragraphs(text)
    docrefs = len(DOCREF_RE.findall(text))
    words = count_words(text)
    ok = (len(pars) >= min_paragraphs and docrefs >= min_docrefs and words >= min_words)
    return ok, len(pars), docrefs, words

# Детектор «извинений/отказов»
APOLOGY_PATTERNS = [
    r"\bне могу\b", r"\bне удалось\b", r"\bя не\b.*\bмогу\b",
    r"\bоснован[оы] на предоставленных данных\b", r"\bне представляется возможным\b"
]
def looks_like_refusal(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in APOLOGY_PATTERNS)

def select_main_investigator(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    invs = state.get("investigators", []) or []
    def score(p):
        pos = (p.get("position") or "").lower()
        s = 0
        if "следователь" in pos: s += 3
        if "по особо важным делам" in pos: s += 1
        s += p.get("confidence", 0)
        return s
    if invs:
        invs = sorted(invs, key=score, reverse=True)
        return invs[0]
    return None

def select_main_prosecutor(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pros = state.get("prosecutors", []) or []
    pros = [p for p in pros if "прокурор" in (p.get("position") or "").lower()]
    if pros:
        pros = sorted(pros, key=lambda x: x.get("confidence", 0), reverse=True)
        return pros[0]
    return None

def compose_final_document(state: Dict[str, Any], ustanovil_body: str) -> str:
    from .prompts import OFFENSE_DEFAULT_ARTICLE  # to avoid cycle
    cm = state.get("case_meta", {}) or {}
    city = cm.get("city")
    erdr = cm.get("erdr")
    date_human = format_kz_date(cm.get("decision_date"))
    investigator = select_main_investigator(state) or {}
    prosecutor = select_main_prosecutor(state) or {}
    offense_article_best = cm.get("offense_article_best") or OFFENSE_DEFAULT_ARTICLE

    agreed = ""
    if prosecutor and "прокурор" in (prosecutor.get("position") or "").lower():
        if prosecutor.get("name") and prosecutor.get("position"):
            agreed = f"СОГЛАСОВЫВАЮ {prosecutor['name']}, {prosecutor['position']}"

    loc_date = ""
    if city and date_human:
        loc_date = f"г.{city} {date_human}"
    elif city:
        loc_date = f"г.{city}"
    elif date_human:
        loc_date = date_human

    inv_line_parts = []
    pos = investigator.get("position")
    rank = investigator.get("rank")
    name = investigator.get("name")
    if pos: inv_line_parts.append(pos)
    if rank: inv_line_parts.append(rank)
    if name: inv_line_parts.append(name)
    inv_line = ", ".join(inv_line_parts) if inv_line_parts else ""

    header_lines = []
    header_lines.append("ПОСТАНОВЛЕНИЕ")
    header_lines.append("о квалификации уголовного правонарушения")
    if agreed:
        header_lines.append(agreed)
    if loc_date:
        header_lines.append(loc_date)
    if inv_line:
        header_lines.append(inv_line + ", рассмотрев материалы досудебного расследования " + (f"№{erdr}" if erdr else "№____") + ",")

    body = []
    body.append("УСТАНОВИЛ:")
    body.append(ustanovil_body.strip())

    tail = []
    tail.append("ПОСТАНОВИЛ:")
    point1 = f"1. Уголовное правонарушение по досудебному расследованию {('№' + erdr) if erdr else '№____'} квалифицировать по {offense_article_best}."
    tail.append(point1)
    tail.append("2. Настоящее постановление направить надзирающему прокурору.")
    if name or rank or pos:
        tail.append(f"{name if name else '____'}, {rank if rank else '____'}, {pos if pos else '____'}")

    parts = header_lines + [""] + body + [""] + tail
    final = "\n".join([p for p in parts if p is not None and p != ""])
    pars = paragraphs(ustanovil_body)
    refs = len(DOCREF_RE.findall(ustanovil_body))
    logger.info(f"[FINAL] USTANOVIL: paragraphs={len(pars)}, docrefs={refs}, words={count_words(ustanovil_body)}")
    return final

# Проверка абзацев по потерпевшим (в тексте)
def _victim_paragraph_ok(par: str) -> bool:
    refs = len(DOCREF_RE.findall(par))
    patt = [
        r"привл", r"зарегистр", r"реферал", r"перечисл|перев|USDT|OKX|P2P|Kaspi",
        r"обещ", r"вывод", r"блокир", r"ущерб|сумма|в размере"
    ]
    has_key = any(re.search(p, par, re.IGNORECASE) for p in patt)
    return refs >= 1 and has_key

def missing_victims_by_paragraphs(ustanovil_text: str, victims: List[Dict[str, Any]]) -> List[str]:
    pars = paragraphs(ustanovil_text)
    miss = []
    for v in victims:
        nm = v.get("name")
        if not nm: 
            continue
        ok = False
        for par in pars:
            if nm.lower() in par.lower():
                if _victim_paragraph_ok(par):
                    ok = True
                    break
        if not ok:
            miss.append(nm)
    return miss
