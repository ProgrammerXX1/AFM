# -*- coding: utf-8 -*-
import re, json
from typing import Any, Dict
from pathlib import Path
import fitz  # PyMuPDF
import tiktoken
from fastapi import UploadFile

from .config import MODEL_ENCODING, STORAGE_DIR

def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding(MODEL_ENCODING)
    return len(enc.encode(text))

def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))

def storage_paths(case_id: int) -> Dict[str, Path]:
    base = STORAGE_DIR / str(case_id)
    return {
        "base": base,
        "docs": base / "docs",
        "chunks": base / "chunks",
        "state_dir": base / "state",
        "state": base / "state" / "global_state.json",
    }

def read_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default

def write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    out = []
    empty = 0
    for ln in lines:
        if ln == "":
            empty += 1
            if empty > 1:
                continue
        else:
            empty = 0
        out.append(ln)
    return "\n".join(out).strip()

def extract_text(file: UploadFile, content: bytes) -> str:
    if file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf"):
        with fitz.open(stream=content, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    return content.decode("utf-8", errors="ignore")
