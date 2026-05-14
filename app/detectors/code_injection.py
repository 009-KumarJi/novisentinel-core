"""Code injection detector (regex-based)."""

from __future__ import annotations

import re

from app.detectors.base import DetectionResult

_SHELL_PATTERNS = [
    re.compile(r"\$\([^)]*\)"),
    re.compile(r"`[^`]+`"),
    re.compile(r";\s*(rm|cat|chmod|chown|nc|wget|curl)\s", re.IGNORECASE),
    re.compile(r"\|\s*(sh|bash|zsh)\b"),
    re.compile(r"\$\{IFS\}"),
]
_PYTHON_PATTERNS = [
    re.compile(r"\b(exec|eval|__import__|compile)\s*\("),
    re.compile(r"\b(pickle|cPickle)\.loads\s*\("),
]
_SQL_PATTERNS = [
    re.compile(r";\s*(DROP|DELETE|UPDATE)\s+(TABLE|FROM)\s", re.IGNORECASE),
    re.compile(r"'\s*OR\s+1\s*=\s*1", re.IGNORECASE),
    re.compile(r"\bUNION\s+SELECT\b", re.IGNORECASE),
]
_JS_PATTERNS = [
    re.compile(r"\$\{[A-Za-z_$][A-Za-z0-9_$.]*\(?"),
]


class CodeInjectionDetector:
    detector_name = "code_injection"

    @property
    def ready(self) -> bool:
        return True

    def warm_up(self) -> None:
        return

    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        out: list[DetectionResult] = []
        for label, patterns in [
            ("shell", _SHELL_PATTERNS),
            ("python", _PYTHON_PATTERNS),
            ("sql", _SQL_PATTERNS),
            ("js", _JS_PATTERNS),
        ]:
            for pat in patterns:
                for m in pat.finditer(text):
                    out.append(
                        DetectionResult(
                            detector="code_injection",
                            type=f"code_injection.{label}",
                            text=m.group(0),
                            redacted="[REDACTED:CODE]",
                            start=m.start(),
                            end=m.end(),
                            confidence=0.9,
                            severity="high",
                        )
                    )
        return out
