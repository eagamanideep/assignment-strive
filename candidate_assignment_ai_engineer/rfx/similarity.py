"""Semantic similarity between lead text and OG Group profiles.

Default: TF-IDF (scikit-learn, no downloads, deterministic).
Optional: sentence-transformers MiniLM embeddings when installed and enabled.
"""
from __future__ import annotations

from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .taxonomy import OG_GROUPS

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def group_profiles() -> dict[str, str]:
    return {g: f"{g}. {c['description']} {' '.join(c['keywords'])}" for g, c in OG_GROUPS.items()}


def embeddings_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def text_similarity(a: str, b: str) -> float:
    """TF-IDF cosine between two texts (used for document-vs-summary relevance)."""
    if not a.strip() or not b.strip():
        return 0.0
    m = TfidfVectorizer(stop_words="english").fit_transform([a, b])
    return float(cosine_similarity(m[0], m[1])[0, 0])


def group_similarity(text: str, use_embeddings: bool = False) -> dict[str, float]:
    profiles = group_profiles()
    names, docs = list(profiles), list(profiles.values())
    if use_embeddings and embeddings_available():
        model = _embedder()
        vecs = model.encode([text] + docs, normalize_embeddings=True)
        sims = vecs[1:] @ vecs[0]
    else:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        m = vec.fit_transform(docs + [text])
        sims = cosine_similarity(m[-1], m[:-1])[0]
    return {n: max(float(s), 0.0) for n, s in zip(names, sims)}
