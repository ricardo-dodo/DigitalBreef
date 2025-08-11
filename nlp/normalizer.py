import re
from typing import List

WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[“”‘’\-–—'\"`]+")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = PUNCT_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    return normalize_text(text).split() 