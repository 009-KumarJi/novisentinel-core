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


# ── tolerant restore (LLM mangling) ──────────────────────────────────────────


def test_restore_handles_dropped_brackets():
    m = AnonymizationMap()
    m.placeholder_for("john@a.com", "EMAIL_ADDRESS")
    assert "john@a.com" in m.restore("contact REDACTED_EMAIL_ADDRESS_001 please")


def test_restore_handles_lowercase():
    m = AnonymizationMap()
    m.placeholder_for("john@a.com", "EMAIL_ADDRESS")
    assert "john@a.com" in m.restore("contact <redacted_email_address_001>")


def test_restore_handles_dashes_for_underscores():
    m = AnonymizationMap()
    m.placeholder_for("john@a.com", "EMAIL_ADDRESS")
    assert "john@a.com" in m.restore("contact <REDACTED-EMAIL-ADDRESS-001>")


def test_restore_handles_missing_zero_padding():
    m = AnonymizationMap()
    m.placeholder_for("john@a.com", "EMAIL_ADDRESS")
    assert "john@a.com" in m.restore("contact <REDACTED_EMAIL_ADDRESS_1>")


def test_restore_leaves_unknown_placeholder_intact():
    m = AnonymizationMap()
    m.placeholder_for("john@a.com", "EMAIL_ADDRESS")
    # Unknown placeholder number — no mapping; must not crash or replace blindly
    text = "see <REDACTED_EMAIL_ADDRESS_999>"
    assert m.restore(text) == text


def test_restore_does_not_match_prose():
    """English prose like 'the redacted email address 1 above' must NOT be
    rewritten — otherwise the LLM can be tricked into producing text that
    leaks the original PII at a location the user can't predict."""
    m = AnonymizationMap()
    m.placeholder_for("john@a.com", "EMAIL_ADDRESS")
    prose = "the redacted email address 1 above"
    assert m.restore(prose) == prose
    prose2 = "see redacted email address 1 in the table"
    assert m.restore(prose2) == prose2


# ── overlap dedup (longer span wins) ──────────────────────────────────────────


def test_redact_longer_span_wins_on_overlap():
    """A wider connection-string match must not be shadowed by an inner password."""
    m = AnonymizationMap()
    text = "url postgresql://admin:s3cretpassword@db:5432/x end"
    # Inner narrow match (e.g. GENERIC_PASSWORD-like) — should be dropped
    inner = DetectionResult(
        detector="secrets",
        type="GENERIC_PASSWORD",
        text="s3cretpassword",
        redacted="[GENERIC_PASSWORD]",
        start=text.index("s3cretpassword"),
        end=text.index("s3cretpassword") + len("s3cretpassword"),
        confidence=0.9,
        severity="high",
    )
    outer = DetectionResult(
        detector="secrets",
        type="CONNECTION_STRING",
        text="postgresql://admin:s3cretpassword@db:5432/x",
        redacted="[CONNECTION_STRING]",
        start=text.index("postgresql://"),
        end=text.index("postgresql://") + len("postgresql://admin:s3cretpassword@db:5432/x"),
        confidence=0.99,
        severity="critical",
    )
    result = m.redact(text, [inner, outer])
    assert "postgresql://" not in result
    assert "admin" not in result
    assert "s3cretpassword" not in result
    assert "db:5432" not in result
    # And the outer placeholder must restore the full original
    assert m.restore(result) == text
