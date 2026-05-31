"""
Translation engine for Tibetan Buddhist texts.

Supports multiple LLM providers (Anthropic, OpenAI) and injects
terminology context from the TermsDB to ensure accurate rendering
of specialized vocabulary.
"""

from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from typing import Literal, Optional

from lotsawa.terms.models import TermsDB


TargetLanguage = Literal["zh", "en", "both"]
Provider = Literal["anthropic", "openai"]


SYSTEM_PROMPT = """You are Lotsawa, an expert translator of Tibetan Buddhist texts.
Your translations are:
- Accurate: You follow established scholarly and contemplative translation conventions.
- Respectful: You maintain the ritual and devotional register of the source text.
- Annotated: When a technical term appears, you keep it as-is and add a brief gloss in parentheses on first use if helpful.
- Consistent: You use the exact translations provided in the terminology reference for all listed terms.

When translating to Chinese (zh): use Classical Chinese Buddhist register where appropriate.
When translating to English (en): follow 84000 / Rangjung Yeshe conventions.
When both languages are requested: output a table with three columns — Tibetan | Chinese | English — one sentence per row.

Respond only with the translation. No preamble, no explanation."""


@dataclass
class TranslationResult:
    source: str
    target_language: TargetLanguage
    translation_zh: str = ""
    translation_en: str = ""
    aligned_rows: list[dict] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    terms_injected: int = 0

    def display(self) -> str:
        if self.target_language == "zh":
            return self.translation_zh
        if self.target_language == "en":
            return self.translation_en
        rows = []
        for row in self.aligned_rows:
            rows.append(
                f"{row.get('tibetan','')}\t{row.get('chinese','')}\t{row.get('english','')}"
            )
        return "\n".join(rows)


def _extract_aligned(raw: str) -> list[dict]:
    """Parse a pipe-separated three-column table from LLM output."""
    rows = []
    for line in raw.strip().splitlines():
        line = line.strip().strip("|")
        if not line or line.startswith("---"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) >= 3:
            rows.append({"tibetan": cols[0], "chinese": cols[1], "english": cols[2]})
    return rows


def _detect_tibetan_words(text: str) -> list[str]:
    """
    Extract plausible Wylie-style tokens and Tibetan script words
    from a mixed text for terminology lookup.
    """
    tibetan_script = re.findall(r"[\u0F00-\u0FFF]+", text)
    wylie_tokens = re.findall(r"[a-z][a-z' +]*[a-z]", text.lower())
    return tibetan_script + wylie_tokens


class Translator:
    """
    Translates Tibetan Buddhist text using an LLM backend,
    injecting relevant terminology context from a TermsDB.

    Parameters
    ----------
    db : TermsDB
        Terminology database used to build prompt context.
    provider : Provider
        "anthropic" (default) or "openai".
    model : str | None
        Model name. Defaults to claude-sonnet-4-20250514 / gpt-4o.
    api_key : str | None
        API key. Falls back to env vars ANTHROPIC_API_KEY / OPENAI_API_KEY.
    """

    def __init__(
        self,
        db: TermsDB,
        provider: Provider = "anthropic",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.db = db
        self.provider = provider
        self.model = model or (
            "claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o"
        )
        self._api_key = api_key or self._default_key()

    def _default_key(self) -> str:
        if self.provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY", "")
        return os.environ.get("OPENAI_API_KEY", "")

    def _build_user_prompt(
        self, text: str, target: TargetLanguage, context: str
    ) -> str:
        lang_instruction = {
            "zh": "Translate the following Tibetan text into Chinese.",
            "en": "Translate the following Tibetan text into English.",
            "both": (
                "Translate the following Tibetan text into both Chinese and English. "
                "Format the output as a Markdown table with columns: Tibetan | Chinese | English. "
                "Break the text into sentences or natural phrases — one row per phrase."
            ),
        }[target]

        parts = [lang_instruction]
        if context:
            parts.append(context)
        parts.append(f"\nSource text:\n{text}")
        return "\n\n".join(parts)

    def translate(
        self,
        text: str,
        target: TargetLanguage = "zh",
        extra_terms: Optional[list[str]] = None,
    ) -> TranslationResult:
        """
        Translate a passage of Tibetan Buddhist text.

        Parameters
        ----------
        text : str
            Source text in Tibetan script or mixed Tibetan/Wylie.
        target : TargetLanguage
            "zh", "en", or "both" (returns aligned table).
        extra_terms : list[str] | None
            Additional Wylie/English queries to force-inject into context.

        Returns
        -------
        TranslationResult
        """
        # Build terminology context
        queries = _detect_tibetan_words(text)
        if extra_terms:
            queries.extend(extra_terms)
        context = self.db.build_context(queries)
        terms_injected = len([q for q in queries if self.db.get(q)])

        user_prompt = self._build_user_prompt(text, target, context)
        raw = self._call_llm(user_prompt)

        result = TranslationResult(
            source=text,
            target_language=target,
            provider=self.provider,
            model=self.model,
            terms_injected=terms_injected,
        )

        if target == "zh":
            result.translation_zh = raw.strip()
        elif target == "en":
            result.translation_en = raw.strip()
        else:
            result.aligned_rows = _extract_aligned(raw)
            for row in result.aligned_rows:
                result.translation_zh += row.get("chinese", "") + "\n"
                result.translation_en += row.get("english", "") + "\n"
            result.translation_zh = result.translation_zh.strip()
            result.translation_en = result.translation_en.strip()

        return result

    def _call_llm(self, user_prompt: str) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic(user_prompt)
        return self._call_openai(user_prompt)

    def _call_anthropic(self, user_prompt: str) -> str:
        try:
            import anthropic  # type: ignore
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )
        client = anthropic.Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    def _call_openai(self, user_prompt: str) -> str:
        try:
            import openai  # type: ignore
        except ImportError:
            raise ImportError(
                "openai package not installed. Run: pip install openai"
            )
        client = openai.OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
