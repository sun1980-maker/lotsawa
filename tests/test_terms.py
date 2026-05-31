"""
Tests for lotsawa core modules.

Run: pytest tests/ -v
"""

import json
import pathlib
import pytest
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from lotsawa.terms.models import Term, TermsDB


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def seed_path(tmp_path):
    """Write a minimal seed file and return its path."""
    terms = [
        {
            "tibetan": "རྡོ་རྗེ་གུ་རུ་",
            "wylie": "rdo rje gu ru",
            "english": "Vajra Guru",
            "chinese": "金刚上师",
            "sanskrit": "Vajraguru",
            "definition_en": "The mantra title of Padmasambhava.",
            "definition_zh": "莲花生大士的咒语称号。",
            "tradition": ["Nyingma"],
            "category": "deity",
            "sources": ["Seven-Line Prayer"],
            "notes": "Do not translate vajra as merely diamond.",
        },
        {
            "tibetan": "རྫོགས་ཆེན་",
            "wylie": "rdzogs chen",
            "english": "Dzogchen",
            "chinese": "大圆满",
            "sanskrit": "Mahāsandhi",
            "definition_en": "Great Perfection.",
            "definition_zh": "大圆满。",
            "tradition": ["Nyingma"],
            "category": "doctrine",
            "sources": [],
            "notes": "",
        },
    ]
    p = tmp_path / "test_terms.json"
    p.write_text(json.dumps(terms), encoding="utf-8")
    return p


@pytest.fixture
def db(seed_path):
    return TermsDB.from_json(seed_path)


# ── Term model ─────────────────────────────────────────────────────────────

class TestTerm:
    def test_from_dict_roundtrip(self):
        d = {
            "tibetan": "བླ་མ་",
            "wylie": "bla ma",
            "english": "Lama",
            "chinese": "喇嘛",
            "sanskrit": "Guru",
            "definition_en": "Spiritual teacher.",
            "definition_zh": "上师。",
            "tradition": ["Nyingma"],
            "category": "teacher",
            "sources": [],
            "notes": "",
        }
        term = Term.from_dict(d)
        assert term.tibetan == "བླ་མ་"
        assert term.wylie == "bla ma"
        assert term.to_dict() == d

    def test_prompt_context_includes_fields(self):
        term = Term(
            tibetan="རྡོ་རྗེ་གུ་རུ་",
            wylie="rdo rje gu ru",
            english="Vajra Guru",
            chinese="金刚上师",
            definition_en="The mantra title of Padmasambhava.",
            notes="Do not translate vajra as merely diamond.",
        )
        ctx = term.prompt_context()
        assert "Vajra Guru" in ctx
        assert "金刚上师" in ctx
        assert "Padmasambhava" in ctx
        assert "diamond" in ctx


# ── TermsDB ────────────────────────────────────────────────────────────────

class TestTermsDB:
    def test_load_from_json(self, db):
        assert len(db) == 2

    def test_get_by_wylie(self, db):
        term = db.get("rdo rje gu ru")
        assert term is not None
        assert term.english == "Vajra Guru"

    def test_get_by_tibetan(self, db):
        term = db.get("རྫོགས་ཆེན་")
        assert term is not None
        assert term.chinese == "大圆满"

    def test_get_by_english(self, db):
        term = db.get("Dzogchen")
        assert term is not None
        assert term.wylie == "rdzogs chen"

    def test_get_case_insensitive(self, db):
        assert db.get("DZOGCHEN") is not None
        assert db.get("dzogchen") is not None

    def test_get_missing_returns_none(self, db):
        assert db.get("nonexistent term xyz") is None

    def test_search_substring(self, db):
        results = db.search("chen")
        wylie_hits = [t.wylie for t in results]
        assert "rdzogs chen" in wylie_hits

    def test_build_context_found(self, db):
        ctx = db.build_context(["rdo rje gu ru", "rdzogs chen"])
        assert "Vajra Guru" in ctx
        assert "Dzogchen" in ctx
        assert ctx.startswith("Tibetan Buddhist terminology reference:")

    def test_build_context_missing_returns_empty(self, db):
        ctx = db.build_context(["nonexistent"])
        assert ctx == ""

    def test_persist_roundtrip(self, db, tmp_path):
        out = tmp_path / "out.json"
        db.to_json(out)
        db2 = TermsDB.from_json(out)
        assert len(db2) == len(db)
        t = db2.get("rdo rje gu ru")
        assert t is not None
        assert t.english == "Vajra Guru"

    def test_add_term(self, db):
        new = Term(tibetan="བདེ་བ་ཅན་", wylie="bde ba can", english="Dewachen", chinese="极乐净土")
        db.add(new)
        assert db.get("bde ba can") is not None
        assert len(db) == 3


# ── Seed data sanity check ─────────────────────────────────────────────────

class TestSeedData:
    """Validates the bundled seed JSON against the Term schema."""

    def test_nyingma_core_loads(self):
        seed = pathlib.Path(__file__).parent.parent / "data" / "seeds" / "nyingma_core.json"
        assert seed.exists(), "Seed file missing"
        db = TermsDB.from_json(seed)
        assert len(db) >= 10, "Expected at least 10 seed terms"

    def test_all_terms_have_required_fields(self):
        seed = pathlib.Path(__file__).parent.parent / "data" / "seeds" / "nyingma_core.json"
        db = TermsDB.from_json(seed)
        for term in db.all_terms():
            assert term.tibetan, f"Missing tibetan on {term.wylie}"
            assert term.wylie,   f"Missing wylie on {term.tibetan}"
            assert term.english, f"Missing english on {term.wylie}"
            assert term.chinese, f"Missing chinese on {term.wylie}"

    def test_amitabha_present(self):
        seed = pathlib.Path(__file__).parent.parent / "data" / "seeds" / "nyingma_core.json"
        db = TermsDB.from_json(seed)
        term = db.get("Amitabha")
        assert term is not None
        assert "阿弥陀佛" in term.chinese
