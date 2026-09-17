"""Small text helpers shared by selection and classification."""
from __future__ import annotations

import re
from functools import lru_cache

NEGATION = re.compile(r"\b(not|no|without|excluding|excludes?|except)\b")
SENTENCE_BREAK = re.compile(r"[.;:\n]")


@lru_cache(maxsize=None)
def _pattern(term: str) -> re.Pattern:
    # Short tokens (sis, erp, dbe) need an exact word; longer terms may take suffixes (consult -> consultant).
    tail = r"s?\b" if len(term) <= 4 else r"\w*"
    return re.compile(r"\b" + re.escape(term) + tail, re.IGNORECASE)


def is_negated(text: str, start: int, window: int = 60) -> bool:
    """True if a negation word appears earlier in the same clause, e.g. 'not seeking ... construction'."""
    before = text[max(0, start - window):start]
    clause = SENTENCE_BREAK.split(before)[-1]
    return bool(NEGATION.search(clause.lower()))


def find_terms(text: str, terms: dict[str, int]) -> tuple[dict[str, int], dict[str, int]]:
    """Return ({term: count}, {term: negated_count}) for every term that occurs."""
    hits: dict[str, int] = {}
    negated: dict[str, int] = {}
    for term in terms:
        for m in _pattern(term).finditer(text):
            bucket = negated if is_negated(text, m.start()) else hits
            bucket[term] = bucket.get(term, 0) + 1
    return hits, negated


def weighted_score(hits: dict[str, int], weights: dict[str, int], cap: int = 3) -> float:
    """Sum of weight x occurrences; repeats are capped so one noisy term cannot dominate."""
    return float(sum(weights[t] * min(c, cap) for t, c in hits.items()))


def bullet_lines(text: str) -> list[str]:
    return [l.strip().lstrip("-•*").strip() for l in text.splitlines()
            if l.strip().startswith(("-", "•", "*")) and len(l.strip()) > 3]
