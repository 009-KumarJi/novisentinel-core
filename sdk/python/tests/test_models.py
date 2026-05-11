from novisentinel.models import Detection, ScanResult


def _make_detection(**overrides) -> Detection:
    defaults = {
        "detector": "pii",
        "type": "ssn",
        "text": "123-45-6789",
        "redacted": "[SSN]",
        "start": 0,
        "end": 11,
        "confidence": 0.99,
        "severity": "high",
    }
    return Detection(**{**defaults, **overrides})


def _make_result(**overrides) -> ScanResult:
    defaults = {
        "scan_id": "scan_test",
        "safe": False,
        "risk_level": "high",
        "action": "block",
        "detections": [_make_detection()],
        "redacted_text": "[SSN]",
        "original_length": 11,
        "scan_duration_ms": 10,
    }
    return ScanResult(**{**defaults, **overrides})


class TestConvenienceProperties:
    def test_has_pii_true(self):
        result = _make_result(detections=[_make_detection(detector="pii")])
        assert result.has_pii is True

    def test_has_pii_false(self):
        result = _make_result(detections=[_make_detection(detector="injection")])
        assert result.has_pii is False

    def test_has_injection_true(self):
        result = _make_result(detections=[_make_detection(detector="injection")])
        assert result.has_injection is True

    def test_has_injection_false(self):
        result = _make_result(detections=[_make_detection(detector="pii")])
        assert result.has_injection is False

    def test_has_secrets_true(self):
        result = _make_result(detections=[_make_detection(detector="secrets")])
        assert result.has_secrets is True

    def test_has_toxicity_true(self):
        result = _make_result(detections=[_make_detection(detector="toxicity")])
        assert result.has_toxicity is True

    def test_has_all_false_when_empty(self):
        result = _make_result(detections=[], safe=True, action="allow")
        assert result.has_pii is False
        assert result.has_injection is False
        assert result.has_secrets is False
        assert result.has_toxicity is False

    def test_detections_by_type_filters_correctly(self):
        result = _make_result(
            detections=[
                _make_detection(detector="pii", type="ssn"),
                _make_detection(detector="pii", type="email"),
                _make_detection(detector="secrets", type="api_key"),
            ]
        )
        ssns = result.detections_by_type("ssn")
        assert len(ssns) == 1
        assert ssns[0].type == "ssn"

    def test_detections_by_type_empty(self):
        result = _make_result(detections=[_make_detection(type="ssn")])
        assert result.detections_by_type("email") == []
