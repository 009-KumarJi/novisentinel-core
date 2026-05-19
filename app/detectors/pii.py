import logging
import re
from functools import lru_cache

from app.config import settings
from app.detectors.base import DetectionResult, Detector

logger = logging.getLogger(__name__)

# Entities to detect by default.
# LOCATION and DATE_TIME excluded — too many false positives on benign text
# (e.g. city names in weather queries, relative times like "today").
# Pass them explicitly via config.pii_entities if you need them.
DEFAULT_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "PERSON",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "US_SSN",
    "MEDICAL_LICENSE",
    "URL",
]

# Critical entities that warrant a block action
CRITICAL_ENTITIES = {"US_SSN", "CREDIT_CARD", "IBAN_CODE", "MEDICAL_LICENSE"}
HIGH_ENTITIES = {"EMAIL_ADDRESS", "PHONE_NUMBER", "IP_ADDRESS"}

SEVERITY_MAP = {
    "US_SSN": "critical",
    "CREDIT_CARD": "critical",
    "IBAN_CODE": "critical",
    "MEDICAL_LICENSE": "critical",
    "EMAIL_ADDRESS": "high",
    "PHONE_NUMBER": "high",
    "IP_ADDRESS": "high",
    "PERSON": "medium",
    "LOCATION": "medium",
    "DATE_TIME": "low",
    "URL": "low",
}


@lru_cache(maxsize=1)
def _get_engines():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    logger.info("Loading Presidio analyzer/anonymizer engines (spaCy: %s)", settings.spacy_model)
    nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": settings.spacy_model}],
        }
    ).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


# Fallback SSN detection. Presidio's UsSsnRecognizer gives the dash pattern a
# very low base score (0.05) and only clears its 0.35 threshold with context
# words — unreliable across Presidio versions, so we run an independent
# regex that excludes structurally-invalid SSNs (000/666/9xx area, 00 group,
# 0000 serial) instead of gating on English context.
_SSN_PATTERN = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")


def _ssn_fallback(text: str) -> list[DetectionResult]:
    out: list[DetectionResult] = []
    for m in _SSN_PATTERN.finditer(text):
        out.append(
            DetectionResult(
                detector="pii",
                type="US_SSN",
                text=m.group(0),
                redacted="[US_SSN]",
                start=m.start(),
                end=m.end(),
                confidence=0.9,
                severity="critical",
            )
        )
    return out


class PIIDetector(Detector):
    name = "pii"

    def warm_up(self) -> None:
        _get_engines()

    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        analyzer, _ = _get_engines()
        entities = config.get("pii_entities", DEFAULT_ENTITIES)

        results = analyzer.analyze(text=text, entities=entities, language="en")
        detections = []
        for r in results:
            entity_type = r.entity_type
            matched_text = text[r.start : r.end]
            redacted = f"[{entity_type}]"
            severity = SEVERITY_MAP.get(entity_type, "medium")

            detections.append(
                DetectionResult(
                    detector=self.name,
                    type=entity_type,
                    text=matched_text,
                    redacted=redacted,
                    start=r.start,
                    end=r.end,
                    confidence=round(r.score, 4),
                    severity=severity,
                )
            )

        if "US_SSN" in entities and not any(d.type == "US_SSN" for d in detections):
            detections.extend(_ssn_fallback(text))

        return detections
