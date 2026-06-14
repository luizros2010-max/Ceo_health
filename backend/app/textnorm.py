"""Shared text normalization: accent-folding + lowercasing for alias matching."""
from __future__ import annotations

import re
import unicodedata


def normalize_alias(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace/punctuation for robust matching.

    'Glicemia (jejum)' -> 'glicemia jejum'; 'Colesterol Total' -> 'colesterol total'.
    """
    if text is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    lowered = no_accents.lower()
    # Replace any run of non-alphanumeric chars with a single space.
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    return cleaned.strip()
