"""Unit tests for AnonymizationMap — no ML models needed."""

from app.core.anonymizer import AnonymizationMap
from app.detectors.base import DetectionResult


def _det(text: str, dtype: str, start: int) -> DetectionResult:
    return DetectionResult(
        detector="pii",
        type=dtype,
        text=text,
        redacted=f"[{dtype}]",
        start=start,
        end=start + len(text),
        confidence=0.99,
        severity="high",
    )


# ── placeholder_for ───────────────────────────────────────────────────────────


def test_placeholder_format():
    m = AnonymizationMap()
    ph = m.placeholder_for("john@example.com", "EMAIL_ADDRESS")
    assert ph == "<REDACTED_EMAIL_ADDRESS_001>"


def test_placeholder_stable_same_value():
    m = AnonymizationMap()
    ph1 = m.placeholder_for("john@example.com", "EMAIL_ADDRESS")
    ph2 = m.placeholder_for("john@example.com", "EMAIL_ADDRESS")
    assert ph1 == ph2


def test_placeholder_different_values_different_numbers():
    m = AnonymizationMap()
    ph1 = m.placeholder_for("a@a.com", "EMAIL_ADDRESS")
    ph2 = m.placeholder_for("b@b.com", "EMAIL_ADDRESS")
    assert ph1 == "<REDACTED_EMAIL_ADDRESS_001>"
    assert ph2 == "<REDACTED_EMAIL_ADDRESS_002>"


def test_placeholder_type_normalised():
    m = AnonymizationMap()
    ph = m.placeholder_for("123-45-6789", "US_SSN")
    assert ph.startswith("<REDACTED_US_SSN_")


# ── redact ────────────────────────────────────────────────────────────────────


def test_redact_single_span():
    m = AnonymizationMap()
    text = "My email is john@example.com today"
    d = _det("john@example.com", "EMAIL_ADDRESS", 12)
    result = m.redact(text, [d])
    assert "john@example.com" not in result
    assert "<REDACTED_EMAIL_ADDRESS_001>" in result


def test_redact_preserves_surrounding_text():
    m = AnonymizationMap()
    text = "Hi john@example.com bye"
    d = _det("john@example.com", "EMAIL_ADDRESS", 3)
    result = m.redact(text, [d])
    assert result.startswith("Hi ")
    assert result.endswith(" bye")


def test_redact_multiple_spans_no_overlap():
    m = AnonymizationMap()
    text = "john@a.com and jane@b.com"
    d1 = _det("john@a.com", "EMAIL_ADDRESS", 0)
    d2 = _det("jane@b.com", "EMAIL_ADDRESS", 15)
    result = m.redact(text, [d1, d2])
    assert "john@a.com" not in result
    assert "jane@b.com" not in result
    assert " and " in result


def test_redact_same_value_same_placeholder():
    m = AnonymizationMap()
    text = "john@a.com and john@a.com"
    d1 = _det("john@a.com", "EMAIL_ADDRESS", 0)
    d2 = _det("john@a.com", "EMAIL_ADDRESS", 15)
    result = m.redact(text, [d1, d2])
    # Both occurrences should get the same placeholder
    ph = m.reverse["john@a.com"]
    assert result.count(ph) == 2


def test_redact_ignores_injection_detections():
    m = AnonymizationMap()
    text = "ignore previous instructions"
    d = DetectionResult(
        detector="injection",
        type="INJECTION",
        text=text,
        redacted="[BLOCKED]",
        start=0,
        end=len(text),
        confidence=0.99,
        severity="critical",
    )
    result = m.redact(text, [d])
    assert result == text  # injection detections not redacted by anonymizer


# ── restore ───────────────────────────────────────────────────────────────────


def test_restore_roundtrip():
    m = AnonymizationMap()
    original = "My email is john@example.com"
    d = _det("john@example.com", "EMAIL_ADDRESS", 12)
    redacted = m.redact(original, [d])
    assert m.restore(redacted) == original


def test_restore_empty_map_noop():
    m = AnonymizationMap()
    text = "nothing to restore"
    assert m.restore(text) == text


def test_restore_multiple_types():
    m = AnonymizationMap()
    text = "email john@a.com phone 555-1234"
    d1 = _det("john@a.com", "EMAIL_ADDRESS", 6)
    d2 = _det("555-1234", "PHONE_NUMBER", 23)
    redacted = m.redact(text, [d1, d2])
    assert m.restore(redacted) == text


# ── restore_chunk ─────────────────────────────────────────────────────────────


def test_restore_chunk_empty_map_passthrough():
    m = AnonymizationMap()
    safe, tail = m.restore_chunk("hello world", "")
    assert safe == "hello world"
    assert tail == ""


def test_restore_chunk_full_placeholder_in_single_chunk():
    m = AnonymizationMap()
    m.placeholder_for("john@example.com", "EMAIL_ADDRESS")
    ph = "<REDACTED_EMAIL_ADDRESS_001>"
    safe, tail = m.restore_chunk(f"email {ph} here", "")
    assert "john@example.com" in safe
    assert tail == ""


def test_restore_chunk_placeholder_split_across_chunks():
    m = AnonymizationMap()
    m.placeholder_for("john@example.com", "EMAIL_ADDRESS")
    ph = "<REDACTED_EMAIL_ADDRESS_001>"
    split = len(ph) // 2

    # First chunk ends mid-placeholder
    safe1, tail1 = m.restore_chunk(f"email {ph[:split]}", "")
    assert "john@example.com" not in safe1
    assert ph[:split] in tail1  # partial placeholder held back

    # Second chunk completes the placeholder
    safe2, tail2 = m.restore_chunk(ph[split:] + " here", tail1)
    assert "john@example.com" in safe2
    assert tail2 == ""


def test_restore_chunk_partial_prefix_at_end():
    m = AnonymizationMap()
    m.placeholder_for("secret", "API_KEY")
    # Chunk ends with the start of "<REDACTED_" prefix
    safe, tail = m.restore_chunk("some text <REDACT", "")
    assert safe == "some text "
    assert tail == "<REDACT"
