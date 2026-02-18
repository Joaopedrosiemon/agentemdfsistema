"""Text normalization and processing utilities."""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Lowercase, strip accents, remove extra spaces."""
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_column_name(col: str) -> str:
    """Normalize a column name for mapping."""
    col = normalize_text(col)
    col = col.replace(" ", "_").replace("-", "_")
    col = re.sub(r"[^a-z0-9_]", "", col)
    return col
