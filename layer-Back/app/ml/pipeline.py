# -*- coding: utf-8 -*-
import json
from typing import Dict, Any, List, Tuple, Set
from .config import (
    logger, MARKER_SCAN_CHUNKS, PER_DOC_TOKEN_CAP, BATCH_MAX_FILES, BATCH_MAX_TOKENS,
    ENABLE_PASS2_ON_GAPS, PASS2_PER_DOC_CAP, EXTRACT_MAX_TOKENS,
    STATE_SNIPPET_SIZES, FINAL_MAX_TOKENS, UST_MAX_REFINE_ROUNDS,
    MAX_MODEL_LEN, SYSTEM_BUDGET
)
from .io_utils import storage_paths, read_json, write_json, count_tokens
from .chunking import load_doc_chunks
from .markers import build_doc_markers, cluster_docs_by_markers, bootstrap_victims_from_postanov, find_postanov_chunks
from .batching import plan_pass1, plan_pass2, build_batches_for_docs, log_batches_overview
from .generator import safe_call_generator
from .json_parse import parse_or_retry_json, MD_FENCE_RE
from .merge import merge_victims, link_money_flows_to_victims
from .prompts import make_extraction_prompt, fit_ustanovil_prompt, make_ustanovil_refine_prompt, make_ustanovil_force_victims_prompt, build_ustanovil_state_subset
from .postproc import (
    collapse_repeated_lines, drop_generic_filler, normalize_erdr_mentions,
    ensure_minimum_evidence, compose_final_document, missing_victims_by_paragraphs,
    looks_like_refusal
)

def _strip_md_fences(s: str) -> str:
    m = MD_FENCE_RE.search(s)
    return m.group(1).strip() if m else s

async def run_pipeline(case_id: int) -> Dict[str, Any]:
    paths = storage_paths(case_id)
    paths["state_dir"].mkdir(parents=True, exist_ok=True)

    docs_map = load_doc_chunks(case_id)
    if not docs_map:
        raise RuntimeError("Нет подготовленных документов. Сначала загрузите /cases/{case_id}/documents")

    state = read_json(paths["state"], default={
        "case_meta": {
            "case_id": case_id, "erdr": None, "city": None, "region": None,
            "agency": None, "decision_date": None, "offense_article_best": None
        },
        "investigators": [], "prosecutors": [],
        "actors": [], "victims": [], "events": [],
        "money_flows": [], "pyramid_indicators": [],
        "mechanism_bullets": [], "offense_articles": [],
        "contradictions": [], "notes": []
    })
    logger.info(f"[STATE] initial: actors={len(state.get('actors', []))}, victims={len(state.get('victims', []))}, events={len(state.get('events', []))}")

    # Bootstrap потерпевших из ПОСТАНОВЛЕНИЙ (ожидаемое число)
    boot = bootstrap_victims_from_postanov(docs_map)
    expected_victims = len(boot)
    if boot:
        added_boot = merge_victims(state, boot, limit=500)
        logger.info(f"[BOOTSTRAP] victims from POSTANOV: expected={expected_victims}, merged={added_boot}")
        write_json(paths["state"], state)

    # Кластера и порядок
    doc_markers = build_doc_markers(docs_map, MARKER_SCAN_CHUNKS)
    clusters = cluster_docs_by_markers(doc_markers)
    doc_order: List[str] = [doc_id for cluster in clusters for doc_id in cluster]

    # Pass1
    take_pass1 = plan_pass1(docs_map, PER_DOC_TOKEN_CAP)
    batches_p1 = build_batches_for_docs(docs_map, doc_order, BATCH_MAX_FILES, BATCH_MAX_TOKENS, take_pass1)
    log_batches_overview(batches_p1, "P1")

    used_chunks: Set[tuple] = set()
    def mark_used(batch_docs: List[Dict[str, Any]]):
        for d in batch_docs:
            did = d["doc_id"]
            for ch in d["chunks"]:
                used_chunks.add((did, int(ch["chunk_id"])) )

    async def process_batches(batches: List[List[Dict[str, Any]]], tag: str):
        nonlocal state
        for i, batch_docs in enumerate(batches, 1):
            state_snippet = {
                "case_meta": {k: state.get("case_meta", {}).get(k) for k in ["erdr","city","region","agency","decision_date"]},
                "offense_article_best": state.get("case_meta", {}).get("offense_article_best"),
                "investigators": state.get("investigators", [])[:STATE_SNIPPET_SIZES["investigators"]],
                "prosecutors": state.get("prosecutors", [])[:STATE_SNIPPET_SIZES["prosecutors"]],
                "actors": state.get("actors", [])[:STATE_SNIPPET_SIZES["actors"]],
                "victims": state.get("victims", [])[:STATE_SNIPPET_SIZES["victims"]],
                "pyramid_indicators": state.get("pyramid_indicators", [])[:STATE_SNIPPET_SIZES["pyramid_indicators"]],
            }

            def fit_prompt(section_label):
                local_docs = [ {"doc_id": d["doc_id"], "chunks": list(d["chunks"]) } for d in batch_docs ]
                prompt = make_extraction_prompt(local_docs, state_snippet, batch_id=f"{tag}-{i}" + (f"-{section_label}" if section_label else ""), section=section_label)
                while count_tokens(prompt) + EXTRACT_MAX_TOKENS + SYSTEM_BUDGET > MAX_MODEL_LEN and any(len(d["chunks"]) > 1 for d in local_docs):
                    local_docs.sort(key=lambda d: sum(ch["n_tokens"] for ch in d["chunks"]), reverse=True)
                    for d in local_docs:
                        if len(d["chunks"]) > 1:
                            d["chunks"].pop(); break
                    prompt = make_extraction_prompt(local_docs, state_snippet, batch_id=f"{tag}-{i}" + (f"-{section_label}" if section_label else ""), section=section_label)
                return prompt, local_docs

            def merge_outputs(subouts: List[Dict[str, Any]]):
                def _merge_list(src_key: str, dst_key: str, limit: int = None) -> int:
                    added = 0
                    dst = state.setdefault(dst_key, [])
                    seen = {json.dumps(x, sort_keys=True) for x in dst}
                    for out in subouts:
                        src = out.get(src_key, [])
                        if not isinstance(src, list): continue
                        for it in src:
                            s = json.dumps(it, sort_keys=True)
                            if s not in seen:
                                dst.append(it); seen.add(s); added += 1
                    if limit is not None and len(dst) > limit:
                        dst.sort(key=lambda x: x.get("confidence", 0), reverse=True)
                        del dst[limit:]
                    return added

                victims_in = []
                for out in subouts:
                    items = out.get("victims_add", [])
                    if isinstance(items, list): victims_in.extend(items)
                added_victims = merge_victims(state, victims_in, limit=500)

                added = {
                    "actors": _merge_list("actors_add", "actors", limit=90),
                    "victims": added_victims,
                    "events": _merge_list("events_add", "events", limit=500),
                    "money_flows": _merge_list("money_flows_add", "money_flows", limit=500),
                    "pyramid_indicators": _merge_list("pyramid_indicators_add", "pyramid_indicators", limit=90),
                    "investigators": _merge_list("investigators", "investigators", limit=10),
                    "prosecutors": _merge_list("prosecutors", "prosecutors", limit=10),
                    "mechanism_bullets": _merge_list("mechanism_bullets_add", "mechanism_bullets", limit=50),
                    "offense_articles": _merge_list("offense_articles_add", "offense_articles", limit=20),
                }
                logger.info(f"[{tag}-{i}] merged: {added}")

                # meta_add
                filled = []
                for out in subouts:
                    meta_add = out.get("meta_add") or {}
                    cm = state.setdefault("case_meta", {})
                    for k in ["erdr", "city", "region", "agency", "decision_date"]:
                        if meta_add.get(k) and not cm.get(k):
                            cm[k] = meta_add.get(k); filled.append(k)
                if filled:
                    logger.info(f"[{tag}-{i}] meta filled: {filled}")

                # offense_article_best
                arts = state.get("offense_articles", [])
                if arts:
                    arts.sort(key=lambda x: x.get("confidence", 0), reverse=True)
                    a = arts[0]
                    article_str = f"ст.{a.get('article','')} ч.{a.get('part','')}"
                    if a.get("point"):
                        article_str += f" п.{a.get('point')}"
                    article_str += " УК РК"
                    state["case_meta"]["offense_article_best"] = article_str
                    logger.info(f"[{tag}-{i}] offense_article_best='{article_str}'")

                write_json(paths["state"], state)

            sections = ["vmf", "rest"]
            for sec in sections:
                prompt, local_docs = fit_prompt(sec)
                try:
                    bout = await parse_or_retry_json(
                        first_prompt=prompt,
                        call_fn=lambda p, n_predict: safe_call_generator(
                            p, n_predict,
                            label=f"EXTRACT {tag}-{i}-{sec}",
                            fallback_predict=[1200, 1000, 800, 600, 400]
                        ),
                        n_predict=EXTRACT_MAX_TOKENS,
                        batch_id=f"{tag}-{i}-{sec}",
                        max_retries=3
                    )
                    subouts = [bout]
                except Exception as e:
                    logger.warning(f"[{tag}-{i}-{sec}] JSON fail -> {e}. Split halves.")
                    subouts = []
                    if len(local_docs) > 1:
                        mid = len(local_docs) // 2
                        sub_batches = [local_docs[:mid], local_docs[mid:]]
                        for j, sub in enumerate(sub_batches, start=1):
                            sub_prompt = make_extraction_prompt(sub, state_snippet, batch_id=f"{tag}-{i}.{j}", section=sec)
                            try:
                                sub_out = await parse_or_retry_json(
                                    first_prompt=sub_prompt,
                                    call_fn=lambda p, n_predict: safe_call_generator(
                                        p, n_predict,
                                        label=f"EXTRACT {tag}-{i}.{j}-{sec}",
                                        fallback_predict=[1200, 1000, 800, 600, 400]
                                    ),
                                    n_predict=EXTRACT_MAX_TOKENS,
                                    batch_id=f"{tag}-{i}.{j}-{sec}",
                                    max_retries=3
                                )
                                subouts.append(sub_out)
                            except Exception as e2:
                                logger.error(f"[{tag}-{i}.{j}-{sec}] sub-batch failed: {e2}")
                        if not subouts:
                            for j, single in enumerate(local_docs, start=1):
                                s_prompt = make_extraction_prompt([single], state_snippet, batch_id=f"{tag}-{i}.S{j}", section=sec)
                                try:
                                    s_out = await parse_or_retry_json(
                                        first_prompt=s_prompt,
                                        call_fn=lambda p, n_predict: safe_call_generator(
                                            p, n_predict,
                                            label=f"EXTRACT {tag}-{i}.S{j}-{sec}",
                                            fallback_predict=[1000, 800, 600, 400]
                                        ),
                                        n_predict=min(1000, EXTRACT_MAX_TOKENS),
                                        batch_id=f"{tag}-{i}.S{j}-{sec}",
                                        max_retries=3
                                    )
                                    subouts.append(s_out)
                                except Exception as e3:
                                    logger.error(f"[{tag}-{i}.S{j}-{sec}] single-doc failed: {e3}")
                        if not subouts:
                            raise RuntimeError(f"Модель не вернула валидный JSON на батче {tag}-{i} даже после дробления")
                    else:
                        raise RuntimeError(f"Модель не вернула валидный JSON на батче {tag}-{i} (single-doc)")
                merge_outputs(subouts)
                for d in local_docs:
                    for ch in d["chunks"]:
                        used_chunks.add((d["doc_id"], int(ch["chunk_id"])) )

    await process_batches(batches_p1, "P1")

    total_all_chunks = sum(len(v) for v in docs_map.values())
    total_used = len(used_chunks)
    logger.info(f"[COVERAGE] Pass1: {total_used}/{total_all_chunks} = {(100.0*total_used/total_all_chunks):.1f}%")

    # Pass2 (хвосты)
    if ENABLE_PASS2_ON_GAPS:
        take_pass2 = plan_pass2(docs_map, used_chunks, PASS2_PER_DOC_CAP)
        take_pass2 = {k: v for k, v in take_pass2.items() if v}
        if take_pass2:
            batches_p2 = build_batches_for_docs(docs_map, doc_order, BATCH_MAX_FILES, BATCH_MAX_TOKENS, take_pass2)
            log_batches_overview(batches_p2, "P2")
            await process_batches(batches_p2, "P2")
            logger.info(f"[COVERAGE] Pass2: {len(used_chunks)}/{total_all_chunks} = {(100.0*len(used_chunks)/total_all_chunks):.1f}%")
        else:
            logger.info("[COVERAGE] Pass2: нет непокрытых чанков — пропуск")

    # Если ожидаемых потерпевших больше, чем извлечённых — адресный добор
    extracted_victims = len(state.get("victims", []))
    if expected_victims and extracted_victims < expected_victims:
        logger.info(f"[VICTIMS] extracted {extracted_victims} < expected {expected_victims} -> targeted pass")
        post_chunks = find_postanov_chunks(docs_map)
        if post_chunks:
            # Сформируем мини-батчи только с постановлениями
            include = {}
            for did, chid in post_chunks:
                include.setdefault(did, []).append(chid)
            batches_target = build_batches_for_docs(docs_map, [k for k in include.keys()], max_files=6, max_tokens_in=BATCH_MAX_TOKENS//2, include_chunks=include)
            await process_batches(batches_target, "P1X")
            extracted_victims = len(state.get("victims", []))
            logger.info(f"[VICTIMS] after targeted pass: extracted={extracted_victims}")

    # Линковка потоков и метаданные
    from .postproc import format_kz_date  # lint
    from .postproc import paragraphs      # lint
    from .postproc import DOCREF_RE       # lint
    from .postproc import ERDR_NUM_RE     # lint
    from .postproc import select_main_investigator, select_main_prosecutor  # lint

    # enrich meta и линки
    from .postproc import normalize_erdr_mentions as _norm  # to avoid circular in imports elsewhere
    from .postproc import drop_generic_filler as _drop
    from .postproc import collapse_repeated_lines as _collapse
    from .postproc import ensure_minimum_evidence as _ensure

    from .postproc import format_kz_date as _fmt  # quiet
    from .postproc import paragraphs as _pars     # quiet

    # простая ф-ция из прежнего кода
    from .postproc import select_main_investigator as _smi  # quiet
    from .postproc import select_main_prosecutor as _smp     # quiet

    # enrich meta по текстам
    from .postproc import normalize_erdr_mentions, collapse_repeated_lines, drop_generic_filler
    from .postproc import ensure_minimum_evidence

    # enrich meta fallback
    from .postproc import format_kz_date as fmt

    # (оставляем как есть твой try_enrich_case_meta_from_text из другой части кода)
    from .postproc import normalize_erdr_mentions as norm_erdr
    # у тебя уже есть util try_enrich_case_meta_from_text в другом модуле — не дублирую здесь
    try:
        from .postproc import try_enrich_case_meta_from_text
        try_enrich_case_meta_from_text(state, docs_map)
    except Exception:
        pass

    link_money_flows_to_victims(state)
    write_json(paths["state"], state)

    # «УСТАНОВИЛ» — генерация
    ustanovil_prompt, used_caps = fit_ustanovil_prompt(state, FINAL_MAX_TOKENS)
    raw_ustanovil = await safe_call_generator(ustanovil_prompt, n_predict=FINAL_MAX_TOKENS, label="USTANOVIL", fallback_predict=[2400, 2000, 1600, 1200, 800])

    ustanovil_text = _strip_md_fences(raw_ustanovil).strip()
    if looks_like_refusal(ustanovil_text):
        # мгновенно форсим расширение без извинений
        refine0 = make_ustanovil_refine_prompt(state, ustanovil_text, need_pars=12, need_refs=8, need_words=900)
        ustanovil_text = _strip_md_fences(await safe_call_generator(refine0, n_predict=min(1800, FINAL_MAX_TOKENS), label="USTANOVIL_REFINE#apology", fallback_predict=[1600, 1400, 1200, 800])).strip()

    ustanovil_text = collapse_repeated_lines(ustanovil_text)
    ustanovil_text = drop_generic_filler(ustanovil_text)
    ustanovil_text = normalize_erdr_mentions(ustanovil_text, state.get("case_meta", {}).get("erdr"))

    ok_ev, n_pars, n_refs, n_words = ensure_minimum_evidence(ustanovil_text, min_paragraphs=12, min_docrefs=8, min_words=900)
    logger.info(f"[USTANOVIL] quality: pars={n_pars}, refs={n_refs}, words={n_words}, ok={ok_ev}")

    rounds = 0
    while (not ok_ev) and (rounds < UST_MAX_REFINE_ROUNDS):
        rounds += 1
        need_pars = max(12, n_pars + 3)
        need_refs = max(8, n_refs + 2)
        need_words = max(900, n_words + 200)
        refine_prompt = make_ustanovil_refine_prompt(state, ustanovil_text, need_pars, need_refs, need_words)
        refined = await safe_call_generator(refine_prompt, n_predict=min(2000, FINAL_MAX_TOKENS), label=f"USTANOVIL_REFINE#{rounds}", fallback_predict=[1800, 1600, 1400, 1200, 800])
        refined = _strip_md_fences(refined).strip()
        if looks_like_refusal(refined):
            # повторный захват
            refined = _strip_md_fences(await safe_call_generator(refine_prompt, n_predict=1600, label=f"USTANOVIL_REFINE#{rounds}_noapol", fallback_predict=[1400, 1200, 1000])).strip()
        refined = collapse_repeated_lines(refined)
        refined = drop_generic_filler(refined)
        refined = normalize_erdr_mentions(refined, state.get("case_meta", {}).get("erdr"))
        ustanovil_text = refined
        ok_ev, n_pars, n_refs, n_words = ensure_minimum_evidence(ustanovil_text, min_paragraphs=12, min_docrefs=8, min_words=900)
        logger.info(f"[USTANOVIL] after refine#{rounds}: pars={n_pars}, refs={n_refs}, words={n_words}, ok={ok_ev}")

    # Проверка покрытия потерпевших
    rel_for_cov = build_ustanovil_state_subset(state, used_caps)
    victims_all = [v for v in rel_for_cov.get("victims", []) if v.get("name")]
    miss = missing_victims_by_paragraphs(ustanovil_text, victims_all)
    extra_rounds = 0
    while miss and extra_rounds < 3:
        extra_rounds += 1
        logger.info(f"[USTANOVIL] victims missing details -> {miss}")
        refine2 = make_ustanovil_force_victims_prompt(state, ustanovil_text, miss)
        refined2 = await safe_call_generator(refine2, n_predict=min(2000, FINAL_MAX_TOKENS), label=f"USTANOVIL_FORCE_VICTIMS#{extra_rounds}", fallback_predict=[1800, 1600, 1400, 1200, 800])
        refined2 = _strip_md_fences(refined2).strip()
        refined2 = collapse_repeated_lines(refined2)
        refined2 = drop_generic_filler(refined2)
        refined2 = normalize_erdr_mentions(refined2, state.get("case_meta", {}).get("erdr"))
        ustanovil_text = refined2
        miss = missing_victims_by_paragraphs(ustanovil_text, victims_all)

    final_text = compose_final_document(state, ustanovil_text).replace("```", "").strip()
    word_count = len(final_text.split())

    # покрытие по документам
    per_doc_cov = []
    for doc_id, chunks in docs_map.items():
        total = len(chunks)
        covered = sum(1 for ch in chunks if (doc_id, int(ch["chunk_id"])) in used_chunks)
        per_doc_cov.append((int(doc_id), covered, total, (100.0 * covered / total) if total else 0.0))
    per_doc_cov.sort(key=lambda x: x[0])
    low_cov = [x for x in per_doc_cov if x[3] < 50.0]
    if low_cov:
        logger.info(f"[COVERAGE] LOW per-doc (<50%): {low_cov[:10]} ... total {len(low_cov)}")

    return {
        "case_id": case_id,
        "batches_p1": len(batches_p1),
        "result_words": word_count,
        "state_path": str(paths['state']),
        "coverage_chunks_total": sum(len(v) for v in docs_map.values()),
        "coverage_chunks_used": len(used_chunks),
        "expected_victims": expected_victims,
        "extracted_victims": len(state.get("victims", [])),
        "result": final_text
    }
