# lotsawa 洛扎瓦

**Open-source toolkit for Tibetan Buddhist text translation and study**

Named after the great Tibetan translators (*lo tsā ba* / ལོ་ཙཱ་བ་) who rendered Sanskrit Buddhist scriptures into Tibetan from the 7th century onward — among them Vairocana, Rinchen Zangpo, and Marpa Lotsawa.

---

## What it does

`lotsawa` is a Python library that combines a structured Tibetan Buddhist **terminology database** with an **LLM-powered translation engine** and a **BDRC text fetcher**, enabling:

- Accurate translation of Tibetan Buddhist texts into Chinese and English
- Consistent rendering of technical terms across traditions (Nyingma, Kagyu, Sakya, Gelug)
- Aligned three-column output (Tibetan | Chinese | English) for study and commentary
- Integration with the [BDRC](https://www.bdrc.io) public corpus of digitised Tibetan texts

---

## Quick start

```python
from lotsawa import TermsDB, Translator

# Load the bundled Nyingma core terminology
db = TermsDB.from_file("data/seeds/nyingma_core.json")

# Translate to Chinese
t = Translator(db=db, provider="anthropic")
result = t.translate("རྡོ་རྗེ་གུ་རུ་པདྨ་འབྱུང་གནས་", target="zh")
print(result.translation_zh)

# Three-column aligned output
result = t.translate("ཨོཾ་ཨཱཿཧཱུྃ་བཛྲ་གུ་རུ་པདྨ་སིདྡྷི་ཧཱུྃ།", target="both")
print(result.display())
```

```python
# Search the term database
term = db.get("rdzogs chen")
print(term.prompt_context())
# → རྫོགས་ཆེན་ (rdzogs chen) = Dzogchen / 大圆满 | Sanskrit: Mahāsandhi | Meaning: Great Perfection…

# Fetch a text from BDRC
from lotsawa import fetch_text
doc = fetch_text("MW1KG14700")
for sentence in doc.sentences()[:5]:
    print(sentence)
```

---

## Installation

```bash
pip install lotsawa[anthropic]   # with Anthropic Claude backend
pip install lotsawa[openai]      # with OpenAI GPT backend
pip install lotsawa[all]         # both backends
```

Set your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

---

## Project structure

```
lotsawa/
├── lotsawa/
│   ├── terms/
│   │   └── models.py        # Term dataclass + TermsDB
│   ├── translate/
│   │   └── engine.py        # Translator (Anthropic / OpenAI)
│   └── fetch/
│       └── bdrc.py          # BDRC API client
├── data/
│   └── seeds/
│       └── nyingma_core.json   # 16 core Nyingma terms (seed)
├── tests/
│   └── test_terms.py
└── pyproject.toml
```

---

## Terminology database

The `data/seeds/` directory contains curated JSON term lists. Each term carries:

| Field | Description |
|-------|-------------|
| `tibetan` | Unicode Tibetan script |
| `wylie` | Extended Wylie transliteration |
| `sanskrit` | Sanskrit equivalent (if any) |
| `english` | Standard English rendering |
| `chinese` | Standard Chinese rendering |
| `definition_en` / `definition_zh` | Brief definition in both languages |
| `tradition` | Schools where the term is used |
| `category` | `deity`, `practice`, `doctrine`, `place`, `teacher`, `text`, `object` |
| `sources` | Source texts |
| `notes` | Translation warnings and lineage-specific guidance |

Current seed coverage: **Nyingma core** (Dzogchen, Longchen Nyingtik, Amitabha, Phowa, Terma, key teachers).

Contributions of additional term lists — Kagyu, Sakya, Gelug, Bön, general Mahayana — are welcome.

---

## How translation works

When you call `Translator.translate()`:

1. **Term detection** — the engine scans the source text for Tibetan script tokens and Wylie fragments, looking them up in the TermsDB.
2. **Context injection** — matched terms are prepended to the LLM prompt as a structured glossary: `རྫོགས་ཆེན་ (rdzogs chen) = Dzogchen / 大圆满 | Meaning: Great Perfection…`
3. **LLM translation** — Claude or GPT receives the glossary + source text with a system prompt instructing it to use the provided renderings exactly.
4. **Structured output** — for `target="both"`, the result is parsed into an aligned three-column table.

This approach avoids the most common LLM translation errors for Buddhist texts: rendering *vajra* as "diamond", *rigpa* as "knowledge", or conflating Dzogchen and Mahamudra terminology.

---

## Contributing

All contributions are welcome:

- **Term lists**: Add seed JSON files for other traditions or expand existing ones
- **Translation corrections**: Open an issue if a term rendering is inaccurate or tradition-inappropriate  
- **Fetch sources**: Add connectors for other open Buddhist text corpora (84000, CBETA, etc.)
- **Tests**: Coverage for the translate and fetch modules

Please read [CONTRIBUTING.md](docs/CONTRIBUTING.md) before submitting a pull request.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Acknowledgements

- [BDRC](https://www.bdrc.io) — Buddhist Digital Resource Center, for the open digitisation of Tibetan texts
- [84000](https://84000.co) — for translation conventions and the Tibetan Buddhist Resource Center glossary  
- [Rangjung Yeshe Dictionary](https://rywiki.tsadra.org) — the definitive community Tibetan-English Buddhist dictionary
- The *lo tsā ba* tradition, without whom none of this would exist
