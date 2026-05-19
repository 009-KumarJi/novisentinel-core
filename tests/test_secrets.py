from app.detectors.secrets import SecretsDetector

detector = SecretsDetector()


def _scan(text):
    return detector.scan(text, {})


def test_openai_key_detected():
    text = "Use sk-" + "a" * 48 + " for the API call"
    results = _scan(text)
    assert any(r.type == "OPENAI_KEY" for r in results)
    assert results[0].severity == "critical"


def test_openai_proj_key_detected():
    text = "key: sk-proj-" + "b" * 40
    results = _scan(text)
    assert any(r.type == "OPENAI_KEY" for r in results)


def test_anthropic_key_detected():
    text = "sk-ant-" + "x" * 90 + " is the key"
    results = _scan(text)
    assert any(r.type == "ANTHROPIC_KEY" for r in results)


def test_aws_key_detected():
    text = "Access key: AKIA" + "A" * 16
    results = _scan(text)
    assert any(r.type == "AWS_ACCESS_KEY" for r in results)


def test_github_token_detected():
    text = "ghp_" + "Z" * 36
    results = _scan(text)
    assert any(r.type == "GITHUB_TOKEN" for r in results)


def test_stripe_key_detected():
    text = "sk_live_" + "a" * 24
    results = _scan(text)
    assert any(r.type == "STRIPE_KEY" for r in results)


def test_private_key_detected():
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAK...\n-----END RSA PRIVATE KEY-----"
    results = _scan(text)
    assert any(r.type == "PRIVATE_KEY" for r in results)


def test_jwt_detected():
    # eyJ... three dot-separated base64url segments
    header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    payload = "eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    sig = "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"Token: {header}.{payload}.{sig}"
    results = _scan(text)
    assert any(r.type == "JWT_TOKEN" for r in results)


def test_generic_password_detected():
    results = _scan("password=supersecret123")
    assert any(r.type == "GENERIC_PASSWORD" for r in results)


def test_generic_password_case_insensitive():
    results = _scan("PASSWORD: MyP@ssw0rd!")
    assert any(r.type == "GENERIC_PASSWORD" for r in results)


def test_clean_text_no_detections():
    results = _scan("The weather today is sunny and warm.")
    assert results == []


def test_redaction_shows_prefix():
    text = "sk-" + "a" * 48
    results = _scan(text)
    assert results[0].redacted.startswith("[OPENAI_KEY:sk-a")
    assert "***" in results[0].redacted


def test_multiple_secrets_detected():
    text = "AKIA" + "B" * 16 + " and sk_test_" + "c" * 24
    results = _scan(text)
    types = {r.type for r in results}
    assert "AWS_ACCESS_KEY" in types
    assert "STRIPE_KEY" in types


def test_postgres_connection_string_detected():
    text = "DATABASE_URL=postgresql://admin:s3cret@db.example.com:5432/mydb"
    results = _scan(text)
    conn = [r for r in results if r.type == "CONNECTION_STRING"]
    assert conn, "expected CONNECTION_STRING detection"
    assert "admin" in conn[0].text and "s3cret" in conn[0].text
    assert "db.example.com" in conn[0].text
    assert conn[0].severity == "critical"


def test_mongodb_srv_connection_string_detected():
    text = "uri = mongodb+srv://user:p%40ssword@cluster0.mongodb.net/test"
    results = _scan(text)
    assert any(r.type == "CONNECTION_STRING" for r in results)


def test_redis_connection_string_detected():
    text = "redis://default:abc123XYZ@redis.example.com:6379"
    results = _scan(text)
    assert any(r.type == "CONNECTION_STRING" for r in results)


def test_jdbc_connection_string_detected():
    text = "jdbc:postgresql://localhost:5432/db?user=admin&password=s3cret"
    results = _scan(text)
    assert any(r.type == "CONNECTION_STRING" for r in results)


def test_plain_url_without_credentials_not_a_connection_string():
    text = "Connect to redis://localhost:6379 for cache."
    results = _scan(text)
    assert not any(r.type == "CONNECTION_STRING" for r in results)
