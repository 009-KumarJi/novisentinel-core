import re
import asyncio
import logging
from functools import lru_cache
from app.detectors.base import Detector, DetectionResult
from app.config import settings

logger = logging.getLogger(__name__)

# Rule-based patterns grouped by attack category
INJECTION_PATTERNS: list[tuple[str, str, str]] = [
    # (category, regex_pattern, description)
    ("OVERRIDE",    r"ignore\s+(?:(?:all|previous|prior)\s+)+(?:instructions?|prompts?|context|rules?)|ignore\s+(?:all|previous|prior)\s+(?:instructions?|prompts?|context|rules?)", "Instruction override"),
    ("OVERRIDE",    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", "Disregard override"),
    ("OVERRIDE",    r"forget\s+(your\s+)?(previous\s+)?(instructions?|training|rules?)",  "Forget instructions"),
    ("OVERRIDE",    r"do\s+not\s+follow\s+(your\s+)?(previous\s+)?instructions?",         "Do not follow"),
    ("ROLE_HIJACK", r"you\s+are\s+now\s+(a\s+|an\s+)?(?!assistant|helpful)",              "Role hijack"),
    ("ROLE_HIJACK", r"pretend\s+(you\s+are|to\s+be)\s+",                                  "Pretend role"),
    ("ROLE_HIJACK", r"act\s+as\s+(a\s+|an\s+)?(different|new|evil|unrestricted)",         "Act as override"),
    ("ROLE_HIJACK", r"your\s+(new\s+)?role\s+is\s+",                                       "New role assignment"),
    ("JAILBREAK",   r"\bDAN\s+mode\b",                                                     "DAN jailbreak"),
    ("JAILBREAK",   r"developer\s+mode\s+(enabled|on|activated)",                          "Developer mode"),
    ("JAILBREAK",   r"jailbreak(ed|ing)?\b",                                               "Jailbreak keyword"),
    ("JAILBREAK",   r"no\s+restrictions?\s+(mode|enabled|on)",                             "No restrictions"),
    ("EXFIL",       r"(repeat|print|output|show|reveal|display)\s+(everything|all)?\s*(above|before|prior|your\s+system\s+prompt)", "Prompt exfiltration"),
    ("EXFIL",       r"(reveal|show|print)\s+(your\s+)?(system\s+)?prompt",                "System prompt leak"),
    ("EXFIL",       r"what\s+(are\s+your\s+|were\s+you\s+given\s+)(instructions?|rules?)", "Instruction leak"),
]

_COMPILED = [
    (cat, re.compile(pat, re.IGNORECASE), desc)
    for cat, pat, desc in INJECTION_PATTERNS
]


@lru_cache(maxsize=1)
def _get_pipeline():
    from transformers import pipeline
    logger.info("Loading injection model: %s", settings.injection_model)
    return pipeline(
        "text-classification",
        model=settings.injection_model,
        device=-1,  # CPU
    )


class InjectionDetector(Detector):
    name = "injection"

    def warm_up(self) -> None:
        _get_pipeline()

    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        # Layer 1: rule-based (fast, synchronous)
        for category, pattern, description in _COMPILED:
            match = pattern.search(text)
            if match:
                return [DetectionResult(
                    detector=self.name,
                    type=category,
                    text=match.group(0),
                    redacted="[INJECTION_ATTEMPT]",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.97,
                    severity="critical",
                )]
        return []

    async def scan_async(self, text: str, config: dict) -> list[DetectionResult]:
        """Full async scan: rules first, then ML if no rule match."""
        rule_results = self.scan(text, config)
        if rule_results:
            return rule_results

        # Layer 2: ML classifier for subtle injections
        threshold = config.get("injection_threshold", settings.injection_threshold)
        try:
            pipe = _get_pipeline()
            result = await asyncio.to_thread(pipe, text[:512])  # truncate for model limits
            label = result[0]["label"].upper()
            score = result[0]["score"]

            if label == "INJECTION" and score >= threshold:
                return [DetectionResult(
                    detector=self.name,
                    type="SUBTLE_INJECTION",
                    text=text[:100] + ("..." if len(text) > 100 else ""),
                    redacted="[INJECTION_ATTEMPT]",
                    start=0,
                    end=len(text),
                    confidence=round(score, 4),
                    severity="critical",
                )]
        except Exception:
            pass  # ML failure is non-fatal; rule layer still ran

        return []
