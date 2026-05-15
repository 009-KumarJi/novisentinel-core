"""Stable-placeholder anonymizer for proxy requests/responses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.detectors.base import DetectionResult

_REDACTED_PREFIX = "<REDACTED_"
_REDACTABLE_DETECTORS = frozenset({"pii", "secrets", "urls", "custom"})


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
        """Replace detected spans with stable placeholders (highest-offset first)."""
        redactable = sorted(
            [d for d in detections if d.detector in _REDACTABLE_DETECTORS],
            key=lambda d: -d.start,
        )
        result = text
        covered: set[int] = set()
        for d in redactable:
            span = set(range(d.start, d.end))
            if span & covered:
                continue
            placeholder = self.placeholder_for(d.text, d.type)
            result = result[: d.start] + placeholder + result[d.end :]
            covered |= span
        return result

    def restore(self, text: str) -> str:
        """Replace all placeholders with their original values."""
        for placeholder, original in self.mapping.items():
            text = text.replace(placeholder, original)
        return text

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

        # Case 1: unclosed complete prefix somewhere in combined
        idx = combined.rfind(_REDACTED_PREFIX)
        if idx != -1 and ">" not in combined[idx:]:
            return self.restore(combined[:idx]), combined[idx:]

        # Case 2: end of combined is a partial leading match of the prefix
        for length in range(len(_REDACTED_PREFIX) - 1, 0, -1):
            if combined.endswith(_REDACTED_PREFIX[:length]):
                cut = len(combined) - length
                return self.restore(combined[:cut]), combined[cut:]

        return self.restore(combined), ""
