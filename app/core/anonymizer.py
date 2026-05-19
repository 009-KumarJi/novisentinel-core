"""Stable-placeholder anonymizer for proxy requests/responses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.detectors.base import DetectionResult

_REDACTED_PREFIX = "<REDACTED_"
_REDACTABLE_DETECTORS = frozenset({"pii", "secrets", "urls", "custom"})

# Tolerant placeholder matcher — survives LLM transformations: lowercase,
# dashes/spaces in place of underscores, optional angle brackets, dropped
# zero-padding (`<REDACTED_EMAIL_1>` vs `<REDACTED_EMAIL_001>`).
#
# Hard constraints to prevent prose like "the redacted email address 1
# above" from triggering a substitution:
#   - REDACTED must be at a word boundary (not mid-word).
#   - When angle brackets are absent, the prefix must use `_` or `-` as
#     separators (English prose uses spaces). The bracketed form accepts
#     spaces because some LLMs reformat "<REDACTED_EMAIL_001>" as
#     "< REDACTED EMAIL 001 >".
_PLACEHOLDER_RE = re.compile(
    r"(?:"
    r"<\s*REDACTED[_\-\s]+([A-Z][A-Z0-9]*(?:[_\-\s]+[A-Z0-9]+)*?)[_\-\s]+(\d{1,4})\s*>"
    r"|"
    r"\bREDACTED[_\-]+([A-Z][A-Z0-9]*(?:[_\-]+[A-Z0-9]+)*?)[_\-]+(\d{1,4})\b"
    r")",
    re.IGNORECASE,
)


@dataclass
class AnonymizationMap:
    """Bidirectional map: placeholder <-> original value, with stable assignment."""

    mapping: dict[str, str] = field(default_factory=dict)  # placeholder -> original
    reverse: dict[str, str] = field(default_factory=dict)  # original -> placeholder
    counters: dict[str, int] = field(default_factory=dict)  # type -> count

    @property
    def is_empty(self) -> bool:
        return not self.mapping

    def placeholder_for(self, value: str, type_name: str) -> str:
        """Return stable placeholder for value; create one on first encounter."""
        if value in self.reverse:
            return self.reverse[value]
        safe_type = re.sub(r"[^A-Z0-9]", "_", type_name.upper())
        n = self.counters.get(safe_type, 0) + 1
        self.counters[safe_type] = n
        placeholder = f"<REDACTED_{safe_type}_{n:03d}>"
        self.mapping[placeholder] = value
        self.reverse[value] = placeholder
        return placeholder

    def redact(self, text: str, detections: list[DetectionResult]) -> str:
        """Replace detected spans with stable placeholders.

        When matches overlap, the *longer* span wins — otherwise a narrow inner
        match (e.g. a password span inside a full connection string) would shadow
        the broader secret and leak the rest of the URI.
        """
        candidates = [d for d in detections if d.detector in _REDACTABLE_DETECTORS]

        selected: list[DetectionResult] = []
        covered: set[int] = set()
        for d in sorted(candidates, key=lambda d: (-(d.end - d.start), d.start)):
            span = set(range(d.start, d.end))
            if span & covered:
                continue
            selected.append(d)
            covered |= span

        result = text
        for d in sorted(selected, key=lambda d: -d.start):
            placeholder = self.placeholder_for(d.text, d.type)
            result = result[: d.start] + placeholder + result[d.end :]
        return result

    def restore(self, text: str) -> str:
        """Replace placeholders with their original values.

        Tolerant to LLM transformations: lowercase, dashes/spaces in place of
        underscores, dropped angle brackets, missing zero-padding.
        `<REDACTED_EMAIL_001>`, `redacted email 1`, `REDACTED-EMAIL-1` all map
        back to the same original.
        """
        if not self.mapping:
            return text

        def _canonical(type_token: str, n: int) -> str:
            t = re.sub(r"[\s\-]+", "_", type_token.upper()).strip("_")
            return f"<REDACTED_{t}_{n:03d}>"

        def _sub(m: re.Match) -> str:
            # Either group pair fires depending on which alternative matched.
            type_token = m.group(1) or m.group(3)
            num = m.group(2) or m.group(4)
            if not type_token or not num:
                return m.group(0)
            key = _canonical(type_token, int(num))
            return self.mapping.get(key, m.group(0))

        return _PLACEHOLDER_RE.sub(_sub, text)

    def restore_chunk(self, incoming: str, tail: str) -> tuple[str, str]:
        """
        Restore placeholders that may span SSE chunk boundaries.

        tail    — buffered suffix from the previous call (partial placeholder)
        incoming — new text from the current chunk

        Returns (safe_to_yield, new_tail_buffer)
        """
        if self.is_empty:
            return tail + incoming, ""

        combined = tail + incoming
        lower = combined.lower()
        prefix_lc = _REDACTED_PREFIX.lower()

        # Case 1: unclosed complete prefix somewhere in combined
        idx = lower.rfind(prefix_lc)
        if idx == -1:
            # Try bare form (no leading `<`) — LLMs sometimes drop angle brackets
            idx = lower.rfind(prefix_lc[1:])
        if idx != -1 and ">" not in combined[idx:] and "\n" not in combined[idx:]:
            # Only hold back if the tail looks like an unfinished placeholder
            # (alnum/underscore/dash/space after the prefix). Otherwise flush.
            after = combined[idx + len(prefix_lc) :]
            if re.match(r"^[A-Za-z0-9_\-\s]*$", after):
                return self.restore(combined[:idx]), combined[idx:]

        # Case 2: end of combined is a partial leading match of the prefix
        for length in range(len(_REDACTED_PREFIX) - 1, 0, -1):
            if lower.endswith(prefix_lc[:length]):
                cut = len(combined) - length
                return self.restore(combined[:cut]), combined[cut:]

        return self.restore(combined), ""
