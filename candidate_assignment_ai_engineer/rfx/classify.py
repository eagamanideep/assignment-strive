"""Hybrid classifier: weighted keywords (explainable) + similarity (robust to wording).

Decision order:
  1. Reject gate  - trades/construction language with no consulting intent.
  2. Group ranking - 0.7 * keyword score + 0.3 * similarity, both normalised.
  3. Review policy - low confidence, close runner-up, staffing, split scope, trades words.
"""
from __future__ import annotations

import math

from .models import Lead, Result, Selection
from .select_doc import is_supporting_file
from .similarity import group_similarity
from .taxonomy import ANTI_CONSULTING, CONSULTING_CUES, OG_GROUPS, REJECT_TERMS, REVIEW_GROUPS
from .text import bullet_lines, find_terms, weighted_score

KEYWORD_WEIGHT, SIMILARITY_WEIGHT = 0.7, 0.3
SECONDARY_DOC_WEIGHT = 0.5
MATCH_THRESHOLD = 60      # confidence below this -> Needs Review
CLOSE_MARGIN = 0.15       # runner-up within 15% of primary -> Needs Review
REJECT_THRESHOLD = 6.0
EVIDENCE_SCALE = 40.0    # raw keyword score at which evidence strength reaches ~63%


def _sources(lead: Lead, selection: Selection) -> list[tuple[str, float]]:
    """Texts to score with their weights: metadata + selected doc count fully, other docs half."""
    sources = [(f"{lead.title}\n{lead.summary}", 1.0), (selection.selected.text, 1.0)]
    sources += [(d.text, SECONDARY_DOC_WEIGHT) for d in lead.documents if d is not selection.selected]
    return [(t, w) for t, w in sources if t.strip()]


def _score_terms(sources, weights: dict[str, int]):
    score, hits, negated = 0.0, {}, {}
    for text, w in sources:
        h, n = find_terms(text, weights)
        score += w * weighted_score(h, weights)
        for t, c in h.items():
            hits[t] = hits.get(t, 0) + c
        for t, c in n.items():
            negated[t] = negated.get(t, 0) + c
    return score, hits, negated


def _top_terms(hits: dict[str, int], weights: dict[str, int], k: int = 4) -> list[str]:
    return sorted(hits, key=lambda t: (weights[t] * hits[t], weights[t]), reverse=True)[:k]


def _smart_summary(lead: Lead, selection: Selection, group_terms: list[str]) -> str:
    buyer = lead.metadata.get("buyer")
    lead_line = lead.summary or selection.selected.text.split("\n\n")[0].strip()
    bullets = bullet_lines(selection.selected.text)
    # Prefer scope bullets that mention the winning group's vocabulary.
    ranked = sorted(bullets, key=lambda b: sum(t in b.lower() for t in group_terms), reverse=True)[:3]
    parts = [f"{buyer}: {lead_line}" if buyer else lead_line]
    if ranked:
        parts.append("Key scope: " + "; ".join(ranked) + ".")
    return " ".join(parts)


def classify(lead: Lead, selection: Selection, use_embeddings: bool = False) -> Result:
    sources = _sources(lead, selection)
    full_text = "\n".join(t for t, _ in sources)
    rationale: list[str] = []
    flags: list[str] = []

    top = selection.scores[0]
    doc_note = f"Selected '{top.name}' as the scope document (score {top.total:.1f}"
    if len(selection.scores) > 1:
        doc_note += f"; runner-up '{selection.scores[1].name}' {selection.scores[1].total:.1f}"
    rationale.append(doc_note + ").")

    # --- 1. Keyword + similarity ranking -------------------------------------------------
    kw_scores, kw_hits = {}, {}
    for group, cfg in OG_GROUPS.items():
        kw_scores[group], kw_hits[group], _ = _score_terms(sources, cfg["keywords"])
    sim_scores = group_similarity(full_text, use_embeddings)
    kw_max, sim_max = max(kw_scores.values()) or 1.0, max(sim_scores.values()) or 1.0
    combined = {
        g: KEYWORD_WEIGHT * kw_scores[g] / kw_max + SIMILARITY_WEIGHT * sim_scores[g] / sim_max
        for g in OG_GROUPS
    }
    ranked = sorted(combined, key=combined.get, reverse=True)
    primary, runner_up = ranked[0], ranked[1]
    margin = (combined[primary] - combined[runner_up]) / (combined[primary] or 1.0)
    strength = 1 - math.exp(-kw_scores[primary] / EVIDENCE_SCALE)  # diminishing returns on more hits
    confidence = round(30 + 45 * strength + 25 * margin)

    primary_terms = _top_terms(kw_hits[primary], OG_GROUPS[primary]["keywords"])
    if primary_terms:
        rationale.append(f"{primary} signals: " + ", ".join(f"'{t}'" for t in primary_terms) + ".")
    else:
        rationale.append(f"{primary} chosen on semantic similarity only; no taxonomy keywords matched.")

    # --- 2. Reject gate ------------------------------------------------------------------
    reject_score, reject_hits, reject_negated = _score_terms(sources, REJECT_TERMS)
    consult_score, _, _ = _score_terms(sources, CONSULTING_CUES)
    anti_consulting = any(p in full_text.lower() for p in ANTI_CONSULTING)
    if reject_negated:
        rationale.append(
            "Ignored negated non-target terms: " + ", ".join(f"'{t}'" for t in reject_negated) + "."
        )

    classification = "Strategic Match"
    if reject_score >= REJECT_THRESHOLD and (anti_consulting or reject_score > 2 * consult_score):
        classification, primary = "Reject", "Reject"
        confidence = min(97, round(70 + reject_score))
        rationale.append(
            "Non-target trades work: " + ", ".join(f"'{t}'" for t in _top_terms(reject_hits, REJECT_TERMS, 5))
            + (" and the solicitation explicitly excludes consulting." if anti_consulting else ".")
        )
        alternates = ranked[:3]
    else:
        alternates = ranked[1:4]
        # --- 3. Review policy ----------------------------------------------------------------
        if not primary_terms:
            flags.append("no_keyword_evidence")
        if reject_score >= 3:
            flags.append("trades_language")
            rationale.append("Some non-target trades language present; confirm this is advisory work.")
        if confidence < MATCH_THRESHOLD:
            flags.append("low_confidence")
            rationale.append(f"Confidence {confidence} is below the {MATCH_THRESHOLD} match threshold.")
        if margin < CLOSE_MARGIN:
            flags.append("close_alternate")
            rationale.append(f"{runner_up} scored close to {primary}; reviewer should confirm the group.")
        if primary in REVIEW_GROUPS:
            flags.append("policy_review_group")
            rationale.append(f"{primary} leads are routed to human review by policy.")
        if is_supporting_file(top.name):
            flags.append("no_primary_solicitation")
            rationale.append(
                f"Best scope document '{top.name}' is a supporting file (appendix/exhibit/addendum); "
                "the main solicitation may be missing from the packet."
            )
        if selection.ambiguous:
            flags.append("scope_split_across_documents")
            rationale.append("Scope appears split across multiple documents; confirm the selected file.")
        if flags:
            classification = "Needs Review"
        else:
            rationale.append(f"Clear lead over {runner_up} (margin {margin:.0%}).")

    return Result(
        classification=classification,
        primary_og_group=primary,
        alternate_og_groups=alternates,
        confidence_score=max(0, min(100, confidence)),
        smart_summary=_smart_summary(lead, selection, primary_terms),
        rationale=rationale,
        selected_document=selection.selected.name,
        group_scores={g: round(combined[g], 3) for g in ranked},
        flags=flags,
    )
