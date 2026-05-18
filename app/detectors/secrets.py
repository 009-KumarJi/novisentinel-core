import re

from app.detectors.base import DetectionResult, Detector

# (label, compiled_pattern, severity)
# If pattern defines a capture group, group(1) is treated as the secret span.
# This lets context-aware patterns match "aws_secret_access_key='...'"
# while only redacting the inner key value.
_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("OPENAI_KEY", re.compile(r"sk-[a-zA-Z0-9]{48}|sk-proj-[a-zA-Z0-9_\-]{40,}"), "critical"),
    ("ANTHROPIC_KEY", re.compile(r"sk-ant-[a-zA-Z0-9\-]{90,}"), "critical"),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "critical"),
    (
        "AWS_SECRET_KEY",
        re.compile(
            r"aws_secret_access_key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
            re.IGNORECASE,
        ),
        "critical",
    ),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pors]_[a-zA-Z0-9]{36,}\b|github_pat_[a-zA-Z0-9_]{82,}"), "critical"),
    ("SLACK_TOKEN", re.compile(r"\bxox[bpars]-[0-9]{10,}-[0-9a-zA-Z\-]+"), "critical"),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"), "critical"),
    ("STRIPE_KEY", re.compile(r"\bsk_(?:live|test)_[a-zA-Z0-9]{24,}\b"), "critical"),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "critical"),
    ("JWT_TOKEN", re.compile(r"\beyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\b"), "high"),
    ("GENERIC_PASSWORD", re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S{8,}", re.IGNORECASE), "high"),
]


class SecretsDetector(Detector):
    name = "secrets"

    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        results = []
        for label, pattern, severity in _PATTERNS:
            group_idx = 1 if pattern.groups >= 1 else 0
            for match in pattern.finditer(text):
                matched = match.group(group_idx)
                # Redact all but first 4 chars
                visible = matched[:4] if len(matched) > 4 else matched
                redacted = f"[{label}:{visible}***]"
                results.append(
                    DetectionResult(
                        detector=self.name,
                        type=label,
                        text=matched,
                        redacted=redacted,
                        start=match.start(group_idx),
                        end=match.end(group_idx),
                        confidence=0.99,
                        severity=severity,
                    )
                )
        return results
