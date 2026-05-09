import pytest
from unittest.mock import patch, MagicMock
from app.detectors.toxicity import ToxicityDetector

detector = ToxicityDetector()


def _mock_scores(**kwargs):
    """Return a scores dict with all categories defaulting to 0.0."""
    base = {
        "toxic": 0.0,
        "severe_toxic": 0.0,
        "obscene": 0.0,
        "threat": 0.0,
        "insult": 0.0,
        "identity_hate": 0.0,
    }
    base.update(kwargs)
    return base


def _model_returning(scores: dict):
    m = MagicMock()
    m.predict.return_value = scores
    return m


@pytest.mark.asyncio
async def test_severe_toxic_fires_critical():
    scores = _mock_scores(severe_toxic=0.9)
    with patch("app.detectors.toxicity._load_model", return_value=_model_returning(scores)):
        results = await detector.scan_async("some hateful text", {})
    assert any(r.type == "SEVERE_TOXIC" and r.severity == "critical" for r in results)


@pytest.mark.asyncio
async def test_threat_fires_critical():
    scores = _mock_scores(threat=0.8)
    with patch("app.detectors.toxicity._load_model", return_value=_model_returning(scores)):
        results = await detector.scan_async("I will hurt you", {})
    assert any(r.type == "THREAT" and r.severity == "critical" for r in results)


@pytest.mark.asyncio
async def test_below_threshold_no_detection():
    scores = _mock_scores(severe_toxic=0.1, toxic=0.3)
    with patch("app.detectors.toxicity._load_model", return_value=_model_returning(scores)):
        results = await detector.scan_async("slightly edgy text", {})
    assert results == []


@pytest.mark.asyncio
async def test_medium_toxicity_fires_medium():
    scores = _mock_scores(obscene=0.85)
    with patch("app.detectors.toxicity._load_model", return_value=_model_returning(scores)):
        results = await detector.scan_async("bad word", {})
    assert any(r.type == "OBSCENE" and r.severity == "medium" for r in results)


@pytest.mark.asyncio
async def test_deduplication_keeps_highest_severity():
    # Both severe_toxic (critical) and toxic (high) fire; severe_toxic should win
    scores = _mock_scores(severe_toxic=0.9, toxic=0.8)
    with patch("app.detectors.toxicity._load_model", return_value=_model_returning(scores)):
        results = await detector.scan_async("text", {})
    types = [r.type for r in results]
    assert "SEVERE_TOXIC" in types
    assert "TOXIC" in types


@pytest.mark.asyncio
async def test_disabled_returns_empty():
    with patch("app.detectors.toxicity.settings") as mock_settings:
        mock_settings.toxicity_enabled = False
        results = await detector.scan_async("any text", {})
    assert results == []


@pytest.mark.asyncio
async def test_custom_threshold_overrides_default():
    scores = _mock_scores(obscene=0.75)
    with patch("app.detectors.toxicity._load_model", return_value=_model_returning(scores)):
        # obscene default threshold is 0.8 — score 0.75 normally wouldn't fire
        results_default = await detector.scan_async("text", {})
        # but with a lower threshold it should fire
        results_low = await detector.scan_async("text", {"toxicity_threshold_medium": 0.7})
    assert results_default == []
    assert any(r.type == "OBSCENE" for r in results_low)


@pytest.mark.asyncio
async def test_model_error_returns_empty():
    m = MagicMock()
    m.predict.side_effect = RuntimeError("GPU OOM")
    with patch("app.detectors.toxicity._load_model", return_value=m):
        results = await detector.scan_async("text", {})
    assert results == []


def test_redacted_text():
    scores = _mock_scores(severe_toxic=0.9)
    m = _model_returning(scores)
    with patch("app.detectors.toxicity._load_model", return_value=m):
        results = detector.scan("some hateful text that is quite long indeed yes", {})
    assert results[0].redacted == "[TOXIC_CONTENT]"
