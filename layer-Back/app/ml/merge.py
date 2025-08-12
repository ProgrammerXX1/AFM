# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional, Set
import json

from .markers import (
    norm_phone, norm_email, norm_iban, norm_card, hash_card,
    canonical_name, victim_entity_key, doc_ids_from_refs
)

def _union_doc_refs(a: List[str], b: List[str], cap: Optional[int] = None) -> List[str]:
    """
    Объединение ссылок на документы без дублей, c опциональным ограничением количества.
    """
    seen: Set[str] = set()
    res: List[str] = []
    for x in (a or []) + (b or []):
        if not x or x in seen:
            continue
        seen.add(x)
        res.append(x)
        if cap and len(res) >= cap:
            break
    return res

def _norm_key_val(v: Any) -> str:
    """
    Нормализует значение поля в строку для формирования устойчивого ключа.
    - int/float -> str(v)
    - dict/list -> json.dumps(sort_keys=True)
    - None -> ""
    - прочее -> str(v).strip()
    """
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v).strip()

def _merge_list_of_dicts(
    dst_list: List[Dict[str, Any]],
    new_list: List[Dict[str, Any]],
    key_fields: List[str],
    keep_order_field: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Безопасный мердж списков словарей по набору полей-ключей (key_fields).
    Не мутирует исходные списки. Игнорирует элементы, не являющиеся dict.
    Если keep_order_field задан, приводит его к int и сортирует по нему по возрастанию.
    """
    base: List[Dict[str, Any]] = [it for it in (dst_list or []) if isinstance(it, dict)]
    out: List[Dict[str, Any]] = list(base)
    seen_keys = {tuple(_norm_key_val(it.get(k)) for k in key_fields) for it in base}

    for it in (new_list or []):
        if not isinstance(it, dict):
            continue
        key = tuple(_norm_key_val(it.get(k)) for k in key_fields)
        if key not in seen_keys:
            out.append(it)
            seen_keys.add(key)

    if keep_order_field:
        # привести поле порядка к int, где возможно
        for it in out:
            if keep_order_field in it and not isinstance(it.get(keep_order_field), int):
                try:
                    it[keep_order_field] = int(it[keep_order_field])  # type: ignore[assignment]
                except Exception:
                    # оставляем как есть, уйдёт в хвост сортировки
                    pass
        out.sort(key=lambda x: x.get(keep_order_field, 10**9))  # type: ignore[call-overload]
    return out

def _normalize_steps_order(steps: List[Dict[str, Any]]) -> None:
    """
    Ин-плейс попытка привести steps[*]['order'] к int (если есть).
    Некорректные значения оставляются как есть.
    """
    for s in steps or []:
        if isinstance(s, dict) and "order" in s:
            try:
                s["order"] = int(s["order"])  # type: ignore[assignment]
            except Exception:
                pass

def merge_victims(state: Dict[str, Any], incoming: List[Dict[str, Any]], limit: int = 500) -> int:
    """
    Сливает потерпевших без потерь важной информации:
    - ключ сущности строится через victim_entity_key (iin/iban/card/email/phone/name|dob)
    - пополняет пустые поля
    - объединяет doc_refs без капа на этом этапе
    - steps/transfers/platform_accounts объединяются по ключам без дублей; steps сортируются по order
    - card не храним полностью (только хэш)
    """
    if not incoming:
        return 0

    victims: List[Dict[str, Any]] = state.setdefault("victims", [])

    # индекс существующих по ключу
    idx: Dict[str, int] = {}
    for i, v in enumerate(victims):
        key = v.get("_key") or victim_entity_key(v)
        if key:
            v["_key"] = key
            idx[key] = i

    added = 0
    for nv in incoming:
        # нормализация базовых полей
        nv["name"] = canonical_name(nv.get("name"))
        if nv.get("phone"):
            nv["phone"] = norm_phone(nv["phone"])
        if nv.get("email"):
            nv["email"] = norm_email(nv["email"])
        if nv.get("iban"):
            nv["iban"] = norm_iban(nv["iban"])
        if nv.get("card"):
            cd = norm_card(nv["card"])
            nv["card_hash"] = hash_card(cd) if cd else None

        nv_steps = nv.get("steps") or []
        nv_transfers = nv.get("transfers") or []
        nv_platform = nv.get("platform_accounts") or []

        # приводим порядок шагов к int и дальше сортируем при мердже
        _normalize_steps_order(nv_steps)

        # ключ сущности
        key = victim_entity_key(nv)
        nv["_key"] = key

        if key and key in idx:
            cur = victims[idx[key]]

            # confidence — берём максимум
            cur["confidence"] = max(
                float(cur.get("confidence", 0) or 0.0),
                float(nv.get("confidence", 0) or 0.0)
            )

            # damage_tenge — берём максимум (некоторые источники содержат частичные суммы)
            try:
                d1 = int(cur.get("damage_tenge", 0) or 0)
            except Exception:
                d1 = 0
            try:
                d2 = int(nv.get("damage_tenge", 0) or 0)
            except Exception:
                d2 = 0
            cur["damage_tenge"] = max(d1, d2)

            # заполняем пустые поля из nv
            for fld in ["iin", "phone", "email", "iban", "card_hash", "tg", "dob", "address", "name", "recruiter", "ref_link"]:
                if not cur.get(fld) and nv.get(fld):
                    cur[fld] = nv[fld]

            # doc_refs и индекс документов
            cur["doc_refs"] = _union_doc_refs(cur.get("doc_refs", []), nv.get("doc_refs", []), cap=None)
            cur["_doc_ids"] = sorted(set((cur.get("_doc_ids") or []) + doc_ids_from_refs(cur.get("doc_refs", []))))

            # списки без потерь
            cur["steps"] = _merge_list_of_dicts(cur.get("steps", []), nv_steps, ["order", "action", "date"], keep_order_field="order")
            cur["transfers"] = _merge_list_of_dicts(cur.get("transfers", []), nv_transfers, ["amount", "currency", "asset", "date", "to", "via"])
            cur["platform_accounts"] = _merge_list_of_dicts(cur.get("platform_accounts", []), nv_platform, ["service", "id"])

        else:
            # новый потерпевший
            nv.pop("card", None)  # не храним полный номер карты
            nv["doc_refs"] = list(dict.fromkeys(nv.get("doc_refs", [])))
            nv["_doc_ids"] = doc_ids_from_refs(nv["doc_refs"])
            _normalize_steps_order(nv_steps)
            nv["steps"] = nv_steps
            nv["transfers"] = nv_transfers
            nv["platform_accounts"] = nv_platform
            victims.append(nv)
            if key and key not in idx:
                idx[key] = len(victims) - 1
            added += 1

    # мягкий лимит на количество потерпевших в state
    if limit and len(victims) > limit:
        victims.sort(key=lambda x: float(x.get("confidence", 0) or 0.0), reverse=True)
        del victims[limit:]

    return added

def link_money_flows_to_victims(state: Dict[str, Any]) -> None:
    """
    Пытается привязать каждый money_flow к потерпевшему по:
    - пересечению doc_ids,
    - совпадениям по ФИО в полях from/to,
    - нормализованным phone/email/iban в from/to.
    Записывает ключ потерпевшего в поле mf['victim_key'].
    """
    victims = state.get("victims", []) or []
    flows = state.get("money_flows", []) or []
    if not victims or not flows:
        return

    v_by_key: Dict[Optional[str], Dict[str, Any]] = {v.get("_key"): v for v in victims if v.get("_key")}
    doc_to_vkeys: Dict[str, Set[str]] = {}

    for v in victims:
        vkey = v.get("_key")
        if not vkey:
            continue
        for did in (v.get("_doc_ids") or []):
            doc_to_vkeys.setdefault(did, set()).add(vkey)

    def score_flow_to_victim(mf: Dict[str, Any], vkey: str, v: Dict[str, Any]) -> int:
        s = 0
        # 1) пересечение документов
        mf_docs = set(doc_ids_from_refs(mf.get("doc_refs", [])))
        if mf_docs & set(v.get("_doc_ids") or []):
            s += 3
        # 2) совпадение ФИО в from/to
        nm = (v.get("name") or "").lower()
        if nm:
            for fld in ["from", "to"]:
                val = (mf.get(fld) or "")
                if isinstance(val, str) and nm in val.lower():
                    s += 2
        # 3) нормализованные контакты в from/to
        for fld, norm_fn in [("phone", norm_phone), ("email", norm_email), ("iban", norm_iban)]:
            vval = norm_fn(v.get(fld)) if v.get(fld) else None
            if not vval:
                continue
            vval_s = str(vval).lower()
            for fld2 in ["from", "to"]:
                target = (mf.get(fld2) or "")
                if isinstance(target, str) and vval_s in target.lower():
                    s += 2
        return s

    for mf in flows:
        best_key: Optional[str] = None
        best_score = 0

        # сначала пытаемся по документам
        for did in doc_ids_from_refs(mf.get("doc_refs", [])):
            for vkey in doc_to_vkeys.get(did, set()):
                v = v_by_key.get(vkey)
                if not v:
                    continue
                sc = score_flow_to_victim(mf, vkey, v)
                if sc > best_score:
                    best_score, best_key = sc, vkey

        # если не нашли, грубый проход по всем
        if not best_key:
            for vkey, v in v_by_key.items():
                sc = score_flow_to_victim(mf, vkey, v)
                if sc > best_score:
                    best_score, best_key = sc, vkey

        if best_key:
            mf["victim_key"] = best_key
