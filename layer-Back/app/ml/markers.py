# -*- coding: utf-8 -*-
import re, hashlib
from typing import Optional, Dict, Any, Set, List, Tuple
from collections import defaultdict, deque

# ------------ Базовые маркеры ------------
IIN_RE = re.compile(r"\b\d{12}\b")
PHONE_RE = re.compile(r"\b(?:\+7|8)\s?[\(\s-]?\d{3}[\)\s-]?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b")
IBAN_RE = re.compile(r"\bKZ[0-9A-Z]{18}\b", re.IGNORECASE)
CARD_RE = re.compile(r"\b(?:\d{4}\s?){3}\d{4}\b")
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
TG_RE = re.compile(r"@[\w\d_]{3,32}")
DOCID_IN_REF_RE = re.compile(r"doc:(\d+)\s*#chunk:\d+", re.IGNORECASE)

# ------------ Заголовки/док-типы ------------
POSTANOV_RE = re.compile(r"ПОСТАНОВЛЕНИЕ\s+о признании лица потерпевшим", re.IGNORECASE)
PROTOKOL_VICTIM_RE = re.compile(r"ПРОТОКОЛ\s+допроса\s+потерпевшего", re.IGNORECASE)
TOP_HEADINGS_RE = re.compile(r"^(ПОСТАНОВЛЕНИЕ|ПРОТОКОЛ|Р\s*А\s*П\s*О\s*Р\s*Т|УВЕДОМЛЕНИЕ)\b", re.IGNORECASE | re.MULTILINE)

# ------------ Русские ФИО/даты/деньги ------------
# ФИО: Фамилия Имя Отчество/инициалы, допускаем «-», «Ё/ё»
FIO_RE = re.compile(
    r"\b([А-ЯЁ][а-яё\-]+)\s+([А-ЯЁ][а-яё\-]+)\s+([А-ЯЁ][а-яё\-]+|[А-ЯЁ]\.[А-ЯЁ]\.)\b"
)
DOB_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")
MONEY_RE = re.compile(r"([0-9][0-9\s.\u00A0]{0,15})\s*(?:тенге|тг)\b", re.IGNORECASE)

# Ключевые фразы для сценария из протоколов
PH_REGISTER = re.compile(r"зарегистр", re.IGNORECASE)
PH_OKX = re.compile(r"\bOKX\b", re.IGNORECASE)
PH_USDT = re.compile(r"\bUSDT\b", re.IGNORECASE)
PH_P2P = re.compile(r"\bP2P\b|\bКаспи\b|\bKaspi\b", re.IGNORECASE)
PH_REF = re.compile(r"реферал|реферальн", re.IGNORECASE)
PH_TASKS = re.compile(r"задан", re.IGNORECASE)
PH_WITHDRAW = re.compile(r"вывод|блокир", re.IGNORECASE)

# ------------ Нормализация/ключи ------------
def norm_email(s: Optional[str]) -> Optional[str]:
    return s.strip().lower() if s else None

def norm_phone(s: Optional[str]) -> Optional[str]:
    if not s: return None
    digits = re.sub(r"\D+", "", s)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return "+7" + digits[1:]
    return "+" + digits if digits else None

def norm_iban(s: Optional[str]) -> Optional[str]:
    return s.strip().upper() if s else None

def norm_card(s: Optional[str]) -> Optional[str]:
    if not s: return None
    digits = re.sub(r"\D+", "", s)
    return digits if 12 <= len(digits) <= 19 else None

def hash_card(digits: str) -> str:
    return hashlib.sha1(digits.encode("utf-8")).hexdigest()

def canonical_name(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()

def victim_entity_key(v: Dict[str, Any]) -> Optional[str]:
    for k, norm_fn, tag in [
        ("iin", lambda x: x, "iin"),
        ("iban", norm_iban, "iban"),
        ("card", norm_card, "card"),
        ("email", norm_email, "email"),
        ("phone", norm_phone, "phone"),
    ]:
        val = norm_fn(v.get(k)) if v.get(k) else None
        if val:
            return f"{tag}:{hash_card(val) if k=='card' else val}"
    nm = canonical_name(v.get("name"))
    dob = (v.get("dob") or "").strip() if isinstance(v.get("dob"), str) else None
    if nm and dob:
        return f"name:{nm}|dob:{dob}"
    if nm:
        return f"name:{nm}"
    return None

def doc_ids_from_refs(refs: List[str]) -> List[str]:
    out = []
    for r in refs or []:
        m = DOCID_IN_REF_RE.search(r or "")
        if m: out.append(m.group(1))
    return out

# ------------ Кластеризация по маркерам ------------
def extract_markers_from_text(t: str) -> Set[str]:
    markers: Set[str] = set()
    for rx in (IIN_RE, PHONE_RE, IBAN_RE, CARD_RE, EMAIL_RE, TG_RE):
        for m in rx.findall(t):
            markers.add(m.strip())
    return markers

def build_doc_markers(docs_map: Dict[str, List[Dict[str, Any]]], first_n_chunks: int) -> Dict[str, Set[str]]:
    doc_markers: Dict[str, Set[str]] = {}
    for doc_id, chunks in docs_map.items():
        text = "\n".join(ch.get("text", "") for ch in chunks[:first_n_chunks])
        doc_markers[doc_id] = extract_markers_from_text(text)
    return doc_markers

def cluster_docs_by_markers(doc_markers: Dict[str, Set[str]]) -> List[List[str]]:
    marker_to_docs: Dict[str, List[str]] = defaultdict(list)
    for d, marks in doc_markers.items():
        for m in marks:
            marker_to_docs[m].append(d)

    adj: Dict[str, Set[str]] = defaultdict(set)
    for docs in marker_to_docs.values():
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                a, b = docs[i], docs[j]
                adj[a].add(b); adj[b].add(a)

    visited: Set[str] = set()
    clusters: List[List[str]] = []
    all_docs = sorted(doc_markers.keys(), key=lambda x: int(x))
    for d in all_docs:
        if d in visited: continue
        comp = []
        q = deque([d]); visited.add(d)
        while q:
            cur = q.popleft(); comp.append(cur)
            for nb in adj.get(cur, []):
                if nb not in visited:
                    visited.add(nb); q.append(nb)
        clusters.append(sorted(comp, key=lambda x: int(x)))
    if not any(len(c) > 1 for c in clusters):
        clusters = [[d] for d in all_docs]
    return clusters

# ------------ Извлечение потерпевших из ПОСТАНОВЛЕНИЙ ------------
def extract_victims_from_postanov_text(text: str) -> List[Dict[str, Any]]:
    victims: List[Dict[str, Any]] = []
    # Ищем ближайшие к «потерпевшим» ФИО + (ДР?) + деньги
    # 1) жёсткий матч ФИО
    for m in FIO_RE.finditer(text):
        fio = " ".join(g for g in m.groups() if g)
        window = text[max(0, m.start()-200): m.end()+200]
        dob = None
        dobm = DOB_RE.search(window)
        if dobm: dob = dobm.group(1)
        dmg = 0
        mm = MONEY_RE.search(window)
        if mm:
            dmg_str = re.sub(r"[^\d]", "", mm.group(1))
            if dmg_str.isdigit():
                try:
                    dmg = int(dmg_str)
                except Exception:
                    dmg = 0
        victims.append({
            "name": canonical_name(fio),
            "dob": dob,
            "damage_tenge": dmg if dmg > 0 else 0,
            "doc_refs": [],  # поставим позже на уровне вызова
            "steps": [],
            "platform_accounts": []
        })
    return victims

def find_postanov_chunks(docs_map: Dict[str, List[Dict[str, Any]]]) -> List[Tuple[str,int]]:
    targets: List[Tuple[str,int]] = []
    for doc_id, chunks in docs_map.items():
        for ch in chunks[:6]:
            t = ch.get("text","")
            if POSTANOV_RE.search(t):
                targets.append((doc_id, int(ch.get("chunk_id",0))))
                break
    return targets

def bootstrap_victims_from_postanov(docs_map: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for doc_id, chunks in docs_map.items():
        for ch in chunks[:6]:
            t = ch.get("text","")
            if POSTANOV_RE.search(t):
                vs = extract_victims_from_postanov_text(t)
                for v in vs:
                    v["doc_refs"] = [f"doc:{doc_id}#chunk:{ch.get('chunk_id')}"]
                result.extend(vs)
                break
    return result

# ------------ Шаги из ПРОТОКОЛОВ ------------
def extract_steps_from_protokol(text: str) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    order = 1
    def add(action: str, details: str):
        nonlocal order, steps
        steps.append({"order": order, "date": None, "action": action, "details": details, "doc_refs": []})
        order += 1

    if PH_REF.search(text): add("Получил реферальную ссылку/приглашение", "Указан реферальный канал/привлекающий")
    if PH_REGISTER.search(text): add("Регистрация на платформе", "Регистрация аккаунта (TAKORP/OKX/другое)")
    if PH_OKX.search(text): add("Создание/использование кошелька OKX", "Аккаунт/кошелёк OKX")
    if PH_USDT.search(text): add("Операции с USDT", "Покупка/перевод USDT")
    if PH_P2P.search(text): add("Покупка через P2P/Kaspi", "Использование P2P/Kaspi/банков")
    if PH_TASKS.search(text): add("Выполнение заданий/получение бонусов", "Описаны задания/бонусы")
    if PH_WITHDRAW.search(text): add("Попытка вывода/блокировка", "Попытка вывести средства/блокировка вывода")

    return steps

def find_protokol_chunks(docs_map: Dict[str, List[Dict[str, Any]]]) -> List[Tuple[str,int]]:
    targets: List[Tuple[str,int]] = []
    for doc_id, chunks in docs_map.items():
        for ch in chunks:
            t = ch.get("text","")
            if PROTOKOL_VICTIM_RE.search(t):
                targets.append((doc_id, int(ch.get("chunk_id",0))))
                break
    return targets
