"""
Utility helpers shared across routes and services for the AI Blog Generator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Sequence


TITLE_SEPARATOR_PATTERN = re.compile(r"[,\n\r]+")
MAX_BLOGS_PER_BATCH = 10
MIN_BLOGS_PER_BATCH = 1
PREVIEW_LENGTH = 150


@dataclass(slots=True)
class ParsedTitles:
    """Represents the outcome of parsing user-supplied blog titles."""

    titles: List[str]
    warnings: List[str]


def parse_titles(raw_input: str) -> ParsedTitles:
    """
    Parse free-form text input into a list of candidate blog titles.

    Args:
        raw_input: Text containing titles separated by commas or new lines.

    Returns:
        A :class:`ParsedTitles` instance with cleaned titles and warnings.
    """

    warnings: List[str] = []
    tokens = [token.strip() for token in TITLE_SEPARATOR_PATTERN.split(raw_input) if token.strip()]

    if not tokens:
        warnings.append("No valid titles were provided.")
        return ParsedTitles(titles=[], warnings=warnings)

    unique_titles = unique_preserve_order(tokens)

    if len(unique_titles) > MAX_BLOGS_PER_BATCH:
        warnings.append(f"Only the first {MAX_BLOGS_PER_BATCH} titles will be processed.")

    titles = unique_titles[:MAX_BLOGS_PER_BATCH]

    if len(titles) < MIN_BLOGS_PER_BATCH:
        warnings.append("Enter at least one title to generate a blog.")

    return ParsedTitles(titles=titles, warnings=warnings)


def unique_preserve_order(items: Sequence[str]) -> List[str]:
    """Return a list of unique values while preserving their original order."""

    seen = set()
    unique: List[str] = []
    for item in items:
        if item and item.lower() not in seen:
            unique.append(item)
            seen.add(item.lower())
    return unique


def summarize(content: str, limit: int = PREVIEW_LENGTH) -> str:
    """Trim content to a short preview for card layouts."""

    if len(content) <= limit:
        return content
    return content[: limit - 1].rsplit(" ", 1)[0] + "..."


def normalise_whitespace(content: str) -> str:
    """Collapse excessive whitespace while maintaining paragraphs."""

    content = re.sub(r"\r\n", "\n", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def download_filename(title: str, *, suffix: str = ".txt") -> str:
    """
    Create a filesystem-friendly filename from a blog title.

    Args:
        title: Blog title provided by the user.
        suffix: File extension to use (defaults to ``.txt``).
    """

    safe = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{safe or 'blog'}-{timestamp}{suffix}"


def chunk_text(text: str, width: int = 80) -> Iterable[str]:
    """
    Yield text wrapped at the specified width for plain-text downloads.
    """

    for paragraph in text.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            yield ""
            continue
        line = ""
        for word in paragraph.split():
            if len(line) + len(word) + 1 > width:
                yield line.rstrip()
                line = ""
            line += word + " "
        if line:
            yield line.rstrip()


