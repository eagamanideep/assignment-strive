"""Single entry point: lead packet in, reviewer-ready result out."""
from __future__ import annotations

from pathlib import Path

from .classify import classify
from .extract import lead_from_files, load_lead_dir
from .models import Lead, Result, Selection
from .select_doc import select_document

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_leads"


def run(lead: Lead, use_embeddings: bool = False) -> tuple[Selection, Result]:
    selection = select_document(lead)
    return selection, classify(lead, selection, use_embeddings)


def classify_files(files: dict[str, bytes], use_embeddings: bool = False) -> dict:
    """Endpoint-style call: {filename: bytes} -> output payload."""
    _, result = run(lead_from_files(files), use_embeddings)
    return result.to_payload()


def sample_leads() -> dict[str, Path]:
    return {p.name: p for p in sorted(SAMPLE_DIR.iterdir()) if p.is_dir()}


def run_dir(path: str | Path, use_embeddings: bool = False) -> tuple[Lead, Selection, Result]:
    lead = load_lead_dir(path)
    return (lead, *run(lead, use_embeddings))
