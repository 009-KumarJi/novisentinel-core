SCAN_RESPONSE = {
    "scan_id": "scan_abc123",
    "safe": False,
    "risk_level": "high",
    "action": "block",
    "detections": [
        {
            "detector": "pii",
            "type": "ssn",
            "text": "123-45-6789",
            "redacted": "[SSN]",
            "start": 10,
            "end": 21,
            "confidence": 0.99,
            "severity": "high",
        }
    ],
    "redacted_text": "My SSN is [SSN]",
    "original_length": 21,
    "scan_duration_ms": 42,
}

BATCH_RESPONSE = [
    SCAN_RESPONSE,
    {**SCAN_RESPONSE, "scan_id": "scan_def456", "safe": True, "action": "allow", "detections": []},
]

API_URL = "http://localhost:8000"
API_KEY = "test-key"
