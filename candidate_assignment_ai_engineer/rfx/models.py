"""Plain data objects passed between pipeline stages."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Document:
    name: str
    text: str


@dataclass
class Lead:
    metadata: dict
    documents: list[Document]

    @property
    def summary(self) -> str:
        return self.metadata.get("summary", "")

    @property
    def title(self) -> str:
        return self.metadata.get("program_name", "")


@dataclass
class DocScore:
    name: str
    total: float
    filename: float
    scope_cues: float
    bullets: float
    similarity: float
    length: float


@dataclass
class Selection:
    selected: Document
    scores: list[DocScore]  # sorted best-first
    ambiguous: bool  # top two documents scored too close to call


@dataclass
class Result:
    classification: str
    primary_og_group: str
    alternate_og_groups: list[str]
    confidence_score: int
    smart_summary: str
    rationale: list[str]
    selected_document: str
    group_scores: dict[str, float] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        """The endpoint contract: required fields only."""
        d = asdict(self)
        d.pop("group_scores")
        d.pop("flags")
        return d
