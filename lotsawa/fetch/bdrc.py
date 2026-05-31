"""
Fetch Tibetan Buddhist texts from BDRC (Buddhist Digital Resource Center).

BDRC exposes a public IIIF and REST API at https://iiif.bdrc.io and
https://ldspdi.bdrc.io. This module wraps common queries for:
  - Looking up works by title or BDRC identifier
  - Fetching plain-text content of a volume or chapter
  - Normalising results into a simple TextDocument dataclass

No authentication is required for open-access works.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote

try:
    import requests  # type: ignore
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


BDRC_LDSPDI = "https://ldspdi.bdrc.io"
BDRC_IIIF   = "https://iiif.bdrc.io"
BDRC_BUDA   = "https://purl.bdrc.io/resource"

DEFAULT_TIMEOUT = 15
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "lotsawa/0.1 (https://github.com/yourusername/lotsawa)",
}


@dataclass
class TextDocument:
    """A normalised representation of a BDRC text resource."""
    bdrc_id: str
    title: str
    language: str = "bo"          # ISO 639 code; "bo" = Tibetan
    content: str = ""             # Plain-text body
    source_url: str = ""
    metadata: dict = field(default_factory=dict)

    def sentences(self) -> list[str]:
        """Split content on Tibetan shad (།) sentence markers."""
        parts = re.split(r"།\s*", self.content)
        return [p.strip() for p in parts if p.strip()]

    def __repr__(self) -> str:
        preview = self.content[:80].replace("\n", " ") if self.content else ""
        return f"<TextDocument {self.bdrc_id!r} title={self.title!r} [{preview}…]>"


class BDRCClient:
    """
    Lightweight client for the BDRC public API.

    Usage
    -----
    >>> client = BDRCClient()
    >>> results = client.search("Seven Line Prayer")
    >>> doc = client.fetch_work("MW1KG14700")
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        if not _REQUESTS_AVAILABLE:
            raise ImportError(
                "requests package not installed. Run: pip install requests"
            )
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _get(self, url: str, params: dict | None = None) -> dict | list:
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def search(
        self,
        query: str,
        language: str = "bo",
        max_results: int = 10,
    ) -> list[dict]:
        """
        Search BDRC for texts matching a title query.

        Parameters
        ----------
        query : str
            Title keywords in English, Tibetan, or Wylie.
        language : str
            Primary language filter ("bo" Tibetan, "en" English, "sa" Sanskrit).
        max_results : int
            Maximum number of results to return.

        Returns
        -------
        list[dict]
            Raw BDRC result dicts with 'id', 'prefLabel', 'type' keys.
        """
        url = f"{BDRC_LDSPDI}/query/table/WorksByTitle"
        params = {
            "L_NAME": query,
            "lang": language,
            "pageSize": max_results,
            "format": "json",
        }
        try:
            data = self._get(url, params)
            if isinstance(data, dict):
                return data.get("results", data.get("bindings", []))
            return data[:max_results]
        except Exception as exc:
            raise RuntimeError(f"BDRC search failed for {query!r}: {exc}") from exc

    def fetch_work(self, bdrc_id: str) -> TextDocument:
        """
        Fetch metadata and available plain-text content for a BDRC work ID.

        Parameters
        ----------
        bdrc_id : str
            A BDRC work identifier, e.g. "MW1KG14700".

        Returns
        -------
        TextDocument
        """
        meta_url = f"{BDRC_BUDA}/{bdrc_id}.json"
        try:
            meta = self._get(meta_url)
        except Exception as exc:
            raise RuntimeError(
                f"Could not fetch BDRC metadata for {bdrc_id!r}: {exc}"
            ) from exc

        title = self._extract_title(meta, bdrc_id)
        text_url = f"{BDRC_IIIF}/2/{bdrc_id}/manifest.json"
        content, source_url = self._try_fetch_text(text_url, bdrc_id)

        return TextDocument(
            bdrc_id=bdrc_id,
            title=title,
            content=content,
            source_url=source_url,
            metadata=meta if isinstance(meta, dict) else {},
        )

    def _extract_title(self, meta: dict | list, fallback: str) -> str:
        if not isinstance(meta, dict):
            return fallback
        for key in ("skos:prefLabel", "rdfs:label", "schema:name"):
            val = meta.get(key)
            if isinstance(val, list) and val:
                return str(val[0].get("@value", val[0]))
            if isinstance(val, str):
                return val
        return fallback

    def _try_fetch_text(
        self, manifest_url: str, bdrc_id: str
    ) -> tuple[str, str]:
        """
        Attempt to retrieve plain text from a BDRC IIIF manifest.
        Returns (content, source_url). Content may be empty if unavailable.
        """
        try:
            manifest = self._get(manifest_url)
            if not isinstance(manifest, dict):
                return "", manifest_url

            # Walk manifest sequences → canvases → annotations → text content
            sequences = manifest.get("sequences", [])
            texts: list[str] = []
            for seq in sequences:
                for canvas in seq.get("canvases", [])[:50]:  # cap pages
                    for annotation_list_ref in canvas.get("otherContent", []):
                        al_url = annotation_list_ref.get("@id", "")
                        if not al_url:
                            continue
                        try:
                            al = self._get(al_url)
                            for ann in (al.get("resources") or []):
                                body = ann.get("resource", {})
                                if body.get("@type") == "cnt:ContentAsText":
                                    texts.append(body.get("chars", ""))
                            time.sleep(0.05)  # be polite
                        except Exception:
                            continue
            return "\n".join(texts), manifest_url
        except Exception:
            return "", manifest_url


# ── Convenience helpers ────────────────────────────────────────────────────

def fetch_text(bdrc_id: str) -> TextDocument:
    """Module-level shorthand: fetch a single text by BDRC ID."""
    return BDRCClient().fetch_work(bdrc_id)


def search_texts(query: str, max_results: int = 10) -> list[dict]:
    """Module-level shorthand: search BDRC for texts."""
    return BDRCClient().search(query, max_results=max_results)
