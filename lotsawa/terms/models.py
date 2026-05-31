"""
Core data model for Tibetan Buddhist terminology.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import pathlib


@dataclass
class Term:
    """
    A single Tibetan Buddhist term with multilingual glosses and metadata.

    Attributes
    ----------
    tibetan : str
        Unicode Tibetan script (e.g. "རིན་པོ་ཆེ་").
    wylie : str
        Wylie transliteration (e.g. "rin po che").
    sanskrit : str | None
        Corresponding Sanskrit term, if any.
    chinese : str
        Standard Chinese rendering.
    english : str
        Standard English rendering (Rangjung Yeshe / 84000 preference).
    definition_zh : str
        Brief definition in Chinese (1–2 sentences).
    definition_en : str
        Brief definition in English (1–2 sentences).
    tradition : list[str]
        Relevant schools/traditions, e.g. ["Nyingma", "Kagyu"].
    category : str
        Semantic category: "deity", "practice", "doctrine", "place",
        "teacher", "text", "object", "other".
    sources : list[str]
        Source texts or collections where the term appears.
    notes : str
        Free-form notes, e.g. lineage-specific usage warnings.
    """

    tibetan: str
    wylie: str
    english: str
    chinese: str
    definition_en: str = ""
    definition_zh: str = ""
    sanskrit: Optional[str] = None
    tradition: list[str] = field(default_factory=list)
    category: str = "other"
    sources: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Term":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def prompt_context(self) -> str:
        """Return a compact string suitable for injecting into LLM prompts."""
        parts = [f"{self.tibetan} ({self.wylie}) = {self.english} / {self.chinese}"]
        if self.sanskrit:
            parts.append(f"Sanskrit: {self.sanskrit}")
        if self.definition_en:
            parts.append(f"Meaning: {self.definition_en}")
        if self.notes:
            parts.append(f"Note: {self.notes}")
        return " | ".join(parts)


class TermsDB:
    """
    In-memory database of Tibetan Buddhist terms loaded from JSON seed files.

    Usage
    -----
    >>> db = TermsDB.from_file("data/seeds/nyingma_core.json")
    >>> term = db.get("vajra guru")
    >>> context = db.build_context(["vajra guru", "padmasambhava"])
    """

    def __init__(self, terms: list[Term] | None = None):
        self._by_wylie: dict[str, Term] = {}
        self._by_tibetan: dict[str, Term] = {}
        self._by_english: dict[str, Term] = {}
        for t in (terms or []):
            self._index(t)

    def _index(self, term: Term) -> None:
        self._by_wylie[term.wylie.lower()] = term
        self._by_tibetan[term.tibetan] = term
        self._by_english[term.english.lower()] = term

    def add(self, term: Term) -> None:
        self._index(term)

    def get(self, query: str) -> Optional[Term]:
        """Look up by Wylie, English, or Tibetan script (case-insensitive for text keys)."""
        q = query.strip()
        return (
            self._by_wylie.get(q.lower())
            or self._by_tibetan.get(q)
            or self._by_english.get(q.lower())
        )

    def search(self, query: str) -> list[Term]:
        """Fuzzy substring search across Wylie, English, and Chinese fields."""
        q = query.lower()
        seen: set[str] = set()
        results: list[Term] = []
        for term in self._by_wylie.values():
            if term.wylie in seen:
                continue
            if (
                q in term.wylie.lower()
                or q in term.english.lower()
                or q in term.chinese
                or q in term.tibetan
            ):
                results.append(term)
                seen.add(term.wylie)
        return results

    def build_context(self, queries: list[str]) -> str:
        """
        Build a multi-term context block for LLM prompt injection.
        Returns a newline-separated list of compact term descriptions.
        """
        lines: list[str] = []
        for q in queries:
            t = self.get(q)
            if t:
                lines.append(t.prompt_context())
        if not lines:
            return ""
        return "Tibetan Buddhist terminology reference:\n" + "\n".join(
            f"  • {l}" for l in lines
        )

    def all_terms(self) -> list[Term]:
        return list(self._by_wylie.values())

    # ── Persistence ────────────────────────────────────────────────────────

    def to_json(self, path: str | pathlib.Path) -> None:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.all_terms()], f, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, path: str | pathlib.Path) -> "TermsDB":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls([Term.from_dict(d) for d in data])

    @classmethod
    def from_file(cls, path: str | pathlib.Path) -> "TermsDB":
        """Alias for from_json; convenience for README examples."""
        return cls.from_json(path)

    def __len__(self) -> int:
        return len(self._by_wylie)

    def __repr__(self) -> str:
        return f"<TermsDB {len(self)} terms>"
