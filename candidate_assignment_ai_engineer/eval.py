"""Score the classifier against expected labels in sample_leads/*/metadata.json.

Usage: python eval.py [--embeddings]
"""
from __future__ import annotations

import sys

from rfx.pipeline import run_dir, sample_leads


def evaluate(use_embeddings: bool = False) -> list[dict]:
    rows = []
    for name, path in sample_leads().items():
        lead, _, result = run_dir(path, use_embeddings)
        exp_group = lead.metadata.get("expected_primary_og_group")
        exp_cls = lead.metadata.get("expected_classification")
        rows.append({
            "lead": name,
            "selected_document": result.selected_document,
            "expected_group": exp_group,
            "predicted_group": result.primary_og_group,
            "group_ok": exp_group == result.primary_og_group,
            "expected_class": exp_cls,
            "predicted_class": result.classification,
            "class_ok": exp_cls == result.classification,
            "confidence": result.confidence_score,
            "flags": ", ".join(result.flags),
        })
    return rows


def main() -> int:
    # Windows consoles may use a legacy code page; never crash on non-ASCII lead names.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = evaluate("--embeddings" in sys.argv)
    for r in rows:
        mark = "PASS" if r["group_ok"] and r["class_ok"] else "FAIL"
        print(f"{mark}  {r['lead']:<32} {r['predicted_group']:<20} {r['predicted_class']:<16} "
              f"conf={r['confidence']:<3} doc={r['selected_document']}  {r['flags']}")
    n = len(rows)
    g = sum(r["group_ok"] for r in rows)
    c = sum(r["class_ok"] for r in rows)
    print(f"\nGroup accuracy {g}/{n}   Classification accuracy {c}/{n}")
    return 0 if g == c == n else 1


if __name__ == "__main__":
    sys.exit(main())
