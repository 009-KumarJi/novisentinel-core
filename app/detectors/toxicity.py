import asyncio
import logging
from functools import lru_cache
from app.detectors.base import Detector, DetectionResult
from app.config import settings

logger = logging.getLogger(__name__)

# (category_key, severity, threshold_config_key, default_threshold)
_CATEGORY_CONFIG: list[tuple[str, str, str, float]] = [
    ("severe_toxic",  "critical", "toxicity_threshold_severe", 0.5),
    ("threat",        "critical", "toxicity_threshold_severe", 0.5),
    ("toxic",         "high",     "toxicity_threshold_high",   0.7),
    ("identity_hate", "high",     "toxicity_threshold_high",   0.7),
    ("obscene",       "medium",   "toxicity_threshold_medium", 0.8),
    ("insult",        "medium",   "toxicity_threshold_medium", 0.8),
]


@lru_cache(maxsize=1)
def _load_model():
    from detoxify import Detoxify
    logger.info("Loading toxicity model: %s", settings.toxicity_model)
    return Detoxify(settings.toxicity_model)


class ToxicityDetector(Detector):
    name = "toxicity"

    def warm_up(self) -> None:
        if settings.toxicity_enabled:
            _load_model()

    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        # Sync scan — used only when called directly (not preferred path)
        if not settings.toxicity_enabled:
            return []
        model = _load_model()
        scores = model.predict(text)
        return self._build_detections(text, scores, config)

    async def scan_async(self, text: str, config: dict) -> list[DetectionResult]:
        if not settings.toxicity_enabled:
            return []
        try:
            model = _load_model()
            scores = await asyncio.to_thread(model.predict, text)
            return self._build_detections(text, scores, config)
        except Exception:
            return []

    def _build_detections(self, text: str, scores: dict, config: dict) -> list[DetectionResult]:
        results = []
        for cat_key, severity, threshold_key, default_thresh in _CATEGORY_CONFIG:
            threshold = config.get(threshold_key, getattr(settings, threshold_key, default_thresh))
            score = float(scores.get(cat_key, 0.0))
            if score >= threshold:
                results.append(DetectionResult(
                    detector=self.name,
                    type=cat_key.upper(),
                    text=text[:120] + ("..." if len(text) > 120 else ""),
                    redacted="[TOXIC_CONTENT]",
                    start=0,
                    end=len(text),
                    confidence=round(score, 4),
                    severity=severity,
                ))
        # De-duplicate: if both severe_toxic + toxic fire, keep only highest severity
        seen: set[str] = set()
        deduped = []
        for r in sorted(results, key=lambda x: ("critical", "high", "medium", "low").index(x.severity)):
            if r.type not in seen:
                seen.add(r.type)
                deduped.append(r)
        return deduped
