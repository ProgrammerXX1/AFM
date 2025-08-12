# -*- coding: utf-8 -*-
import json
from typing import Any, Dict, List, Optional, Tuple
from .config import (
    MAX_MODEL_LEN, SYSTEM_BUDGET, FINAL_MAX_TOKENS, UST_STATE_CAPS,
    OFFENSE_DEFAULT_ARTICLE, logger
)
from .io_utils import count_tokens

def _extraction_schema(section: Optional[str]) -> str:
    if section == "vmf":
        return (
            "{"
            '"batch_id":"",'
            '"meta_add":{"erdr":null,"city":null,"region":null,"agency":null,"decision_date":null},'
            '"victims_add":[{"name":"","iin":null,"phone":null,"email":null,"iban":null,"card":null,"tg":null,"dob":null,"address":null,'
            '"recruiter":null,"ref_link":null,"platform_accounts":[{"service":"","id":""}],'
            '"steps":[{"order":1,"date":null,"action":"","details":"","doc_refs":[]}],'
            '"transfers":[{"amount":0,"currency":"KZT","asset":null,"via":null,"to":"","bank":null,"date":null,"doc_refs":[]}],'
            '"damage_tenge":0,"doc_refs":[],"confidence":0.0}],'
            '"money_flows_add":[{"amount":0,"currency":"KZT","from":"","to":"","method":"","asset":null,"date":null,"doc_refs":[],"confidence":0.0}],'
            '"contradictions":[],"notes":[]'
            "}"
        )
    return (
        "{"
        '"batch_id":"",'
        '"meta_add":{"erdr":null,"city":null,"region":null,"agency":null,"decision_date":null},'
        '"investigators":[{"name":"","rank":"","position":"","doc_refs":[],"confidence":0.0}],'
        '"prosecutors":[{"name":"","position":"","doc_refs":[],"confidence":0.0}],'
        '"actors_add":[{"name":"","role":[],"iin":null,"doc_refs":[],"confidence":0.0}],'
        '"events_add":[{"type":"","date":"YYYY-MM-DD","desc":"","doc_refs":[],"confidence":0.0}],'
        '"pyramid_indicators_add":[{"indicator":"","evidence":[],"confidence":0.0}],'
        '"mechanism_bullets_add":[{"order":1,"text":"","doc_refs":[]}],'
        '"offense_articles_add":[{"code":"УК РК","article":"217","part":"2","point":"1","doc_refs":[],"confidence":0.0}],'
        '"contradictions":[],"notes":[]'
        "}"
    )

def make_extraction_prompt(batch_docs: List[Dict[str, Any]], state_snippet: Dict[str, Any], batch_id: str, section: Optional[str] = None) -> str:
    rules_limits = (
        "ПРАВИЛА ВЫВОДА:\n"
        " - ключи/строки в двойных кавычках; null где нет данных; без комментариев; без висячих запятых;\n"
        " - строки ≤ 200 символов; каждый факт снабжай doc_ref 'doc:<doc_id>#chunk:<chunk_id>'.\n"
        " - ЛИМИТЫ МИНИМАЛЬНЫЕ, можно вернуть больше при наличии данных. Не придумывай.\n"
        " - Если встречаются протоколы допросов потерпевших — подробно извлекай steps/transfers.\n"
        " - Для КАЖДОГО потерпевшего, встречающегося в документах батча, ОБЯЗАТЕЛЬНО заполни steps по схеме: "
        "кто привлёк → регистрация (TAKORP/реф/OKX) → переводы (сумма/валюта/куда/через что) → обещания → попытка вывода/блокировка → итоговый ущерб.\n"
        " - Ответ ДОЛЖЕН быть СТРОГО валидным JSON и начинаться символом '{' без преамбул, пояснений и Markdown.\n"
    )
    system = (
        "Ты юрист-аналитик. ДАНО: фрагменты материалов дела.\n"
        "ЗАДАЧА: извлечь факты для квалификации по ст.217 УК РК, с максимальным вниманием к ПОТЕРПЕВШИМ.\n"
        "СТРОГО запрещено писать любые извинения, фразы 'не могу', 'не удалось'. Возвращай только JSON по схеме.\n"
        + rules_limits + "СХЕМА:\n" + _extraction_schema(section)
    )
    state_json = json.dumps(state_snippet, ensure_ascii=False)
    parts = ["=== ИНСТРУКЦИЯ ===", system, "=== GLOBAL_STATE_SNIPPET ===", state_json, "=== ДОКУМЕНТЫ (ПО БАТЧУ) ==="]
    for d in batch_docs:
        lines = [f"## DOC doc_id={d['doc_id']}"]
        for ch in d["chunks"]:
            lines.append(f"[chunk {ch['chunk_id']}]\n{ch['text']}")
        parts.append("\n".join(lines))
    parts.append(f'=== ВЕРНИ ТОЛЬКО JSON! Укажи "batch_id":"{batch_id}" ===')
    if section: parts.append(f"=== СЕКЦИЯ === {section}")
    return "\n\n".join(parts)

def _score_item(it: Dict[str, Any]) -> float:
    base = float(it.get("confidence", 0.0) or 0.0)
    refs = len(it.get("doc_refs", []) or [])
    return base + 0.2 * refs

def _topk(items: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    if k is None or k <= 0 or not items: return items or []
    items = sorted(items, key=_score_item, reverse=True)
    return items[:k]

def build_ustanovil_state_subset(state: Dict[str, Any], caps: Dict[str, int]) -> Dict[str, Any]:
    return {
        "case_meta": state.get("case_meta", {}),
        "actors": _topk(state.get("actors", []), caps.get("actors")),
        "victims": _topk(state.get("victims", []), caps.get("victims")),
        "events": _topk(state.get("events", []), caps.get("events")),
        "money_flows": _topk(state.get("money_flows", []), caps.get("money_flows")),
        "pyramid_indicators": _topk(state.get("pyramid_indicators", []), caps.get("pyramid_indicators")),
        "mechanism_bullets": _topk(state.get("mechanism_bullets", []), caps.get("mechanism_bullets")),
        "offense_articles": _topk(state.get("offense_articles", []), caps.get("offense_articles")),
    }

def _build_victim_template_clause(victims_list: List[Dict[str, Any]]) -> str:
    names = [v.get("name") for v in victims_list if v.get("name")]
    return (
        "• По каждому потерпевшему сформируй ОТДЕЛЬНЫЙ абзац, строго по структуре: "
        "[кто привлёк] → [регистрация (TAKORP/OKX/реф)] → [переводы: суммы/валюта/куда/через что] → "
        "[обещания] → [попытка вывода/блокировка] → [итоговый ущерб] → [(см. doc:..#chunk:..)]. "
        "Запрещено пропускать потерпевших. "
        f"Список: {', '.join(names) if names else '—'}\n"
    )

def make_ustanovil_prompt(state: Dict[str, Any], caps: Optional[Dict[str, int]] = None) -> str:
    cm = state.get("case_meta", {}) or {}
    erdr = cm.get("erdr")
    article = cm.get("offense_article_best") or OFFENSE_DEFAULT_ARTICLE
    rel_state = build_ustanovil_state_subset(state, caps or UST_STATE_CAPS)
    victims_list = [v for v in rel_state.get("victims", []) if v.get("name")]
    victims_clause = _build_victim_template_clause(victims_list)

    spec = (
        "Сформируй ТОЛЬКО содержимую часть раздела 'УСТАНОВИЛ:' (без слова 'УСТАНОВИЛ:' в начале). "
        "Официальный стиль РК. 12–18 абзацев, ≥900 слов, без Markdown и кода.\n\n"
        "СТРОГО запрещены фразы вроде 'я не могу', 'не удалось определить', 'предоставленными данными'.\n"
        "Структура:\n"
        "1) Вступление — кто/где/ЕРДР (если указан)/статья.\n"
        "2) Схема вовлечения — тезисно по шагам (реферал → регистрация/OKX → USDT/P2P → задания/бонусы → попытка вывода/блокировка).\n"
        "3) Потерпевшие — по каждому отдельный абзац (см. требования ниже).\n"
        "4) Завершение — краткое обобщение и ссылка на статью.\n\n"
        "По возможности в каждом абзаце хотя бы один источник в формате (см. doc:<id>#chunk:<id>).\n"
        f"ЕРДР используй ТОЛЬКО если он указан как '{(erdr or '—')}'. Статью: {article}.\n"
        + victims_clause +
        "Верни ТОЛЬКО чистый текст абзацами."
    )

    st = json.dumps(rel_state, ensure_ascii=False)
    facts = []
    for a in rel_state.get("actors", [])[:8]:
        nm = a.get("name"); rl = ", ".join(a.get("role", [])[:2]) if isinstance(a.get("role"), list) else a.get("role")
        dr = (a.get("doc_refs") or [])[:1]
        if nm: facts.append(f"- Организатор/участник: {nm}" + (f" ({rl})" if rl else "") + (f" (см. {dr[0]})" if dr else ""))

    for v in rel_state.get("victims", [])[:12]:
        nm = v.get("name"); dmg = v.get("damage_tenge"); dr = (v.get("doc_refs") or [])[:1]
        if nm: facts.append(f"- Потерпевший: {nm}" + (f", ущерб {dmg} тг" if dmg else "") + (f" (см. {dr[0]})" if dr else ""))

    return (
        "=== ИНСТРУКЦИЯ ===\n" + spec +
        "\n\n=== КОНСПЕКТ ФАКТОВ (опирайся, не копируй дословно) ===\n" + "\n".join(facts) +
        "\n\n=== ДАННЫЕ STATE (ссылки и сущности) ===\n" + st +
        "\n\n=== ВЕРНИ ТОЛЬКО ТЕКСТ РАЗДЕЛА БЕЗ ЗАГОЛОВКА ==="
    )

def fit_ustanovil_prompt(state: Dict[str, Any], predict_budget: int) -> Tuple[str, Dict[str, int]]:
    caps = dict(UST_STATE_CAPS)
    min_caps = {"victims": 40, "events": 60, "money_flows": 40, "actors": 30, "pyramid_indicators": 20, "mechanism_bullets": 12, "offense_articles": 5}
    order = ["victims", "events", "money_flows", "actors", "pyramid_indicators", "mechanism_bullets"]
    while True:
        prompt = make_ustanovil_prompt(state, caps=caps)
        need = count_tokens(prompt) + predict_budget + SYSTEM_BUDGET
        if need <= MAX_MODEL_LEN:
            return prompt, caps
        changed = False
        for k in order:
            cur = caps.get(k, 0)
            if cur > min_caps[k]:
                newv = max(min_caps[k], int(cur * 0.85))
                if newv < cur:
                    caps[k] = newv; changed = True
        if not changed:
            return prompt, caps

def make_ustanovil_refine_prompt(state: Dict[str, Any], draft_text: str, need_pars: int, need_refs: int, need_words: int) -> str:
    cm = state.get("case_meta", {}) or {}
    erdr = cm.get("erdr")
    article = cm.get("offense_article_best") or OFFENSE_DEFAULT_ARTICLE
    rel = build_ustanovil_state_subset(state, {"actors": 25, "victims": 60, "events": 60, "pyramid_indicators": 16, "mechanism_bullets": 12, "money_flows": 25, "offense_articles": 5})
    spec = (
        "Отредактируй и ДОПОЛНИ следующий текст 'УСТАНОВИЛ:' так, чтобы он стал длиннее и доказательнее. "
        f"Цели: абзацев ≥ {need_pars}, ссылок ≥ {need_refs}, слов ≥ {need_words}. "
        "Добавляй только проверяемые детали из данных, особенно по потерпевшим (кто привлёк, регистрация, переводы, обещания, вывод, ущерб). "
        "Каждый новый абзац — по возможности со ссылкой (см. doc:<id>#chunk:<id>). "
        "СТРОГО запрещены фразы 'не могу', 'не удалось', 'основан на предоставленных данных'. "
        f"Статью упоминай кратко: {article}. ЕРДР используй только '{erdr}'. "
        "Верни ТОЛЬКО чистый текст абзацами."
    )
    st = json.dumps(rel, ensure_ascii=False)
    return "=== ИНСТРУКЦИЯ ===\n" + spec + "\n\n=== ДАННЫЕ ДЛЯ ОПОРЫ ===\n" + st + "\n\n=== ЧЕРНОВИК ===\n" + draft_text.strip() + "\n\n=== ВЕРНИ ТОЛЬКО ТЕКСТ ==="

def make_ustanovil_force_victims_prompt(state: Dict[str, Any], draft_text: str, missing_names: List[str]) -> str:
    rel = build_ustanovil_state_subset(state, UST_STATE_CAPS)
    hint = (
        "Добавь РАЗВЁРНУТЫЕ абзацы по следующим потерпевшим (структура: кто привлёк → регистрация → переводы (суммы/валюта/куда/через что) → "
        "обещания → попытка вывода/блокировка → итоговый ущерб → ссылки): "
        + "; ".join(missing_names) + ". Не сокращай уже написанное. Верни раздел целиком. "
        "Запрещены извинения/отказ."
    )
    return "=== ИНСТРУКЦИЯ ===\n" + hint + "\n\n=== ДАННЫЕ ===\n" + json.dumps(rel, ensure_ascii=False) + "\n\n=== ТЕКСТ ===\n" + draft_text.strip() + "\n\n=== ВЕРНИ ТОЛЬКО ТЕКСТ ==="
