"""Document chunking and tokenisation shared by the dense and sparse retrievers."""
import re
from dataclasses import dataclass

from app.domain.document import DocumentRecord

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z$])")
_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")

_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were will with "
    "who which what when where how than then there their they them i my me we our you your".split()
)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    source: str  # document_type value, e.g. "PDS", "Legislation"
    section: str
    text: str

    @property
    def indexed_text(self) -> str:
        # Titles carry the strongest topical signal ("Concessional Contributions Cap"), so both
        # retrievers see title + body.
        return f"{self.title}. {self.text}"


def chunk_document(document: DocumentRecord, max_words: int = 60) -> list[Chunk]:
    """Sentence-packing chunker: greedily packs whole sentences up to max_words."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(document.full_text_excerpt) if s.strip()]
    groups: list[list[str]] = []
    current: list[str] = []
    words = 0
    for sentence in sentences:
        n = len(sentence.split())
        if current and words + n > max_words:
            groups.append(current)
            current, words = [], 0
        current.append(sentence)
        words += n
    if current:
        groups.append(current)

    return [
        Chunk(
            chunk_id=f"{document.document_id}#{i}",
            document_id=document.document_id,
            title=document.title,
            source=document.document_type.value,
            section=f"Passage {i + 1}",
            text=" ".join(group),
        )
        for i, group in enumerate(groups)
    ]


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS]
