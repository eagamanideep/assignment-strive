"""Pick the most SOW-like document in a lead packet.

Each document gets a transparent, additive score so reviewers can see why it won:
  filename hints + scope language + bullet structure + relevance to lead summary + length prior.
"""
from __future__ import annotations

import re

from .models import Document, DocScore, Lead, Selection
from .similarity import text_similarity
from .text import bullet_lines

FILENAME_HINTS = {
    "sow": 4, "scope": 4, "statement_of_work": 4, "rfp": 3, "rfq": 3, "rfi": 2, "ifb": 2,
    "solicitation": 2, "main": 2, "specification": 2,
    "addendum": -2, "exhibit": -1, "appendix": -1, "attachment": -1,
    "pricing": -3, "price": -3, "form": -3, "insurance": -3, "affidavit": -3,
    "w9": -4, "certification": -2, "bond": -3, "map": -2,
}

SCOPE_CUES = [
    "scope of work", "scope of services", "scope", "statement of work", "deliverables",
    "work includes", "services include", "the selected firm", "the selected consultant",
    "consultant will", "contractor shall", "shall provide", "tasks", "requesting proposals",
    "soliciting proposals", "invites proposals", "seeks",
]

SUPPORTING_MARKERS = ("appendix", "addendum", "exhibit", "attachment")

AMBIGUITY_RATIO = 0.75  # runner-up within 75% of winner -> scope likely split across files


def _filename_score(name: str) -> float:
    tokens = re.sub(r"[^a-z0-9]+", "_", name.lower())
    return float(sum(w for hint, w in FILENAME_HINTS.items() if hint in tokens))


def is_supporting_file(name: str) -> bool:
    """Appendices, addenda and exhibits supplement a main solicitation rather than replace it."""
    return any(m in name.lower() for m in SUPPORTING_MARKERS)


def score_document(doc: Document, lead: Lead) -> DocScore:
    text = doc.text.lower()
    filename = _filename_score(doc.name)
    cues = float(min(sum(text.count(c) for c in SCOPE_CUES), 8))
    bullets = float(min(len(bullet_lines(doc.text)), 12))
    reference = f"{lead.title} {lead.summary}"
    similarity = text_similarity(doc.text, reference) if reference.strip() else 0.0
    length = min(len(text) / 1500, 2.0)
    total = filename + 1.0 * cues + 0.5 * bullets + 6.0 * similarity + length
    return DocScore(doc.name, round(total, 2), filename, cues, bullets, round(similarity, 3), round(length, 2))


def select_document(lead: Lead) -> Selection:
    scores = sorted((score_document(d, lead) for d in lead.documents), key=lambda s: s.total, reverse=True)
    by_name = {d.name: d for d in lead.documents}
    ambiguous = (
        len(scores) > 1 and scores[0].total > 0 and scores[1].total >= AMBIGUITY_RATIO * scores[0].total
    )
    return Selection(by_name[scores[0].name], scores, ambiguous)
