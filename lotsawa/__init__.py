"""
lotsawa — Open-source toolkit for Tibetan Buddhist text translation and study.

Named after the great Tibetan translators (lo tsā ba) who rendered Sanskrit
Buddhist scriptures into Tibetan from the 7th century onward.

Quick start
-----------
>>> from lotsawa import TermsDB, Translator
>>> db = TermsDB.from_file("data/seeds/nyingma_core.json")
>>> t = Translator(db=db, provider="anthropic")
>>> result = t.translate("རྡོ་རྗེ་གུ་རུ་", target="both")
>>> print(result.display())
"""

from lotsawa.terms.models import Term, TermsDB
from lotsawa.translate.engine import Translator, TranslationResult
from lotsawa.fetch.bdrc import BDRCClient, TextDocument, fetch_text, search_texts

__version__ = "0.1.0"
__all__ = [
    "Term",
    "TermsDB",
    "Translator",
    "TranslationResult",
    "BDRCClient",
    "TextDocument",
    "fetch_text",
    "search_texts",
]
