# -*- coding: utf-8 -*-
from typing import Dict, List, Any, Set, Tuple
from .config import BATCH_MAX_FILES, BATCH_MAX_TOKENS
from .chunking import tokens_stats
from .config import logger

def build_batches_for_docs(
    docs_map: Dict[str, List[Dict[str, Any]]],
    doc_order: List[str],
    max_files: int,
    max_tokens_in: int,
    include_chunks: Dict[str, List[int]]
) -> List[List[Dict[str, Any]]]:
    batches: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    cur_tokens = 0

    for doc_id in doc_order:
        chunks = docs_map[doc_id]
        idxs = include_chunks.get(doc_id, [])
        if not idxs:
            continue
        take: List[Dict[str, Any]] = []
        total_doc_tokens = 0
        for i in idxs:
            ch = chunks[i]
            take.append(ch); total_doc_tokens += ch["n_tokens"]

        if (len(cur) >= max_files) or (cur_tokens + total_doc_tokens > max_tokens_in and cur):
            batches.append(cur); cur = []; cur_tokens = 0

        cur.append({"doc_id": doc_id, "chunks": take})
        cur_tokens += total_doc_tokens

    if cur: batches.append(cur)
    return batches

def plan_pass1(docs_map: Dict[str, List[Dict[str, Any]]], per_doc_cap: int) -> Dict[str, List[int]]:
    plan: Dict[str, List[int]] = {}
    for doc_id, chunks in docs_map.items():
        acc, toks = [], 0
        for ch in chunks:
            if toks + ch["n_tokens"] > per_doc_cap:
                break
            acc.append(ch["chunk_id"]); toks += ch["n_tokens"]
        plan[doc_id] = acc
    return plan

def plan_pass2(docs_map: Dict[str, List[Dict[str, Any]]], used_set: Set[Tuple[str, int]], per_doc_cap: int) -> Dict[str, List[int]]:
    plan: Dict[str, List[int]] = {}
    for doc_id, chunks in docs_map.items():
        acc, toks = [], 0
        for ch in chunks:
            key = (doc_id, int(ch["chunk_id"]))
            if key in used_set: continue
            if toks + ch["n_tokens"] > per_doc_cap:
                break
            acc.append(ch["chunk_id"]); toks += ch["n_tokens"]
        if acc: plan[doc_id] = acc
    return plan

def log_batches_overview(batches: List[List[Dict[str, Any]]], title: str):
    logger.info(f"[BATCH] {title}: построено батчей: {len(batches)}")
    for i, b in enumerate(batches, 1):
        toks = [ch["n_tokens"] for d in b for ch in d["chunks"]]
        doc_ids = [d["doc_id"] for d in b]
        logger.info(f"[BATCH {title} {i}] файлов: {len(b)}, чанков: {sum(len(d['chunks']) for d in b)}, токены: {tokens_stats(toks)}, docs={doc_ids}")
