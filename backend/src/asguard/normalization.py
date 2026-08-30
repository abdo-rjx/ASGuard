"""Input normalization.

Normalization is the first input stage: it produces a canonical, de-obfuscated
view of user content so that detectors can operate on a stable representation
while the original text is preserved for span-accurate sanitization.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Characters commonly used to evade pattern matching.
_INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u00ad]")
_WHITESPACE_RE = re.compile(r"\s+")
# Base64-ish blob: long runs of base64 alphabet, at least one digit/symbol mix.
_BASE64ISH_RE = re.compile(r"\b[A-Za-z0-9+/=]{24,}\b")
    # Separated-letter obfuscation: i.g.n.o.r.e or i g n o r e
_SEPARATED_WORD_RE = re.compile(r"\b(?:[a-z][\s.\-_*]+){5,}[a-z]\b", re.IGNORECASE)
# Short separated words (2+ letters) — collapsed only when separation was detected.
_SEPARATED_SHORT_RE = re.compile(r"\b(?:[a-z][\s.]+){2,}[a-z]\b")

# Common homoglyph / leet substitutions.
_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "$": "s", "@": "a", "|": "l", "€": "e",
})

# Latin lookalikes of ASCII letters (homoglyph attacks).
_HOMOGLYPHS = {
    "і": "i", "ѕ": "s", "а": "a", "е": "e", "о": "o", "р": "p",
    "с": "c", "у": "y", "һ": "h", "х": "x", "ԁ": "d", "ɡ": "g",
    "ａ": "a", "ｂ": "b", "ｃ": "c", "ｅ": "e", "ｉ": "i", "ｏ": "o",
}


@dataclass
class NormalizedInput:
    """Result of input normalization."""

    original: str
    normalized: str
    flags: list[str] = field(default_factory=list)
    visible_char_ratio: float = 1.0
    base64ish_ratio: float = 0.0
    # All whitespace/punctuation removed — used to catch letter-separated text.
    condensed: str = ""


def normalize(text: str) -> NormalizedInput:
    """Normalize user content for analysis.

    Steps: NFKC unicode folding → homoglyph folding → invisible character
    removal → leetspeak folding → whitespace collapse → lowercase.
    Obfuscation heuristics are recorded as flags; de-obfuscated patterns are
    still detectable in ``normalized``.
    """
    flags: list[str] = []
    if not text:
        return NormalizedInput(original=text, normalized="", flags=flags)

    total_chars = len(text)
    visible = _INVISIBLE_RE.sub("", text)
    if len(visible) != total_chars:
        flags.append("invisible_characters_removed")

    # Unicode fold + homoglyph fold.
    folded = unicodedata.normalize("NFKC", visible).casefold()
    folded = "".join(_HOMOGLYPHS.get(ch, ch) for ch in folded)

    # Leetspeak folding.
    folded = folded.translate(_LEET_MAP)

    # Whitespace collapse + lowercase.
    normalized = _WHITESPACE_RE.sub(" ", folded).strip().lower()

    # Obfuscation heuristics.
    if _SEPARATED_WORD_RE.search(text):
        flags.append("separated_letters")
        # Collapse separated long words…
        collapsed = _SEPARATED_WORD_RE.sub(
            lambda m: re.sub(r"[\s.\-_*]+", "", m.group(0)),
            normalized,
        )
        # …and short separated words (e.g. "a l l" → "all") so injected
        # patterns hidden behind letter separation become visible.
        collapsed = _SEPARATED_SHORT_RE.sub(
            lambda m: re.sub(r"[\s.]+", "", m.group(0)),
            collapsed,
        )
        normalized = collapsed

    base64ish = _BASE64ISH_RE.findall(text)
    base64ish_ratio = sum(len(b) for b in base64ish) / max(total_chars, 1)
    if base64ish_ratio > 0.3:
        flags.append("base64_like_blob")

    visible_char_ratio = len(visible) / max(total_chars, 1)
    condensed = re.sub(r"[^a-z0-9]+", "", normalized)
    if text.strip().lower() != normalized and not flags:
        flags.append("normalized")
    return NormalizedInput(
        original=text,
        normalized=normalized,
        flags=flags,
        visible_char_ratio=visible_char_ratio,
        base64ish_ratio=base64ish_ratio,
        condensed=condensed,
    )
