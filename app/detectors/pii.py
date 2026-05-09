import logging
from functools import lru_cache
from app.detectors.base import Detector, DetectionResult
from app.config import settings

logger = logging.getLogger(__name__)

# Entities to detect by default.
# LOCATION and DATE_TIME excluded — too many false positives on benign text
# (e.g. city names in weather queries, relative times like "today").
# Pass them explicitly via config.pii_entities if you need them.
DEFAULT_ENTITIES = [
    "EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON",
    "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS", "US_SSN",
    "MEDICAL_LICENSE", "URL",
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
    from presidio_anonymizer import AnonymizerEngine
    logger.info("Loading Presidio analyzer/anonymizer engines (spaCy: %s)", settings.spacy_model)
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


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
            matched_text = text[r.start:r.end]
            redacted = f"[{entity_type}]"
            severity = SEVERITY_MAP.get(entity_type, "medium")

            detections.append(DetectionResult(
                detector=self.name,
                type=entity_type,
                text=matched_text,
                redacted=redacted,
                start=r.start,
                end=r.end,
                confidence=round(r.score, 4),
                severity=severity,
            ))

        return detections
