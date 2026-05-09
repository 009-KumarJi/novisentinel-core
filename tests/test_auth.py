from app.core.auth import generate_api_key, hash_key, hash_text


def test_key_starts_with_prefix():
    raw, prefix, _ = generate_api_key()
    assert raw.startswith("nvs_")
    assert prefix == raw[:8]


def test_key_hash_matches():
    raw, _, key_hash = generate_api_key()
    assert hash_key(raw) == key_hash


def test_different_keys_different_hashes():
    _, _, h1 = generate_api_key()
    _, _, h2 = generate_api_key()
    assert h1 != h2


def test_hash_text_is_deterministic():
    assert hash_text("hello") == hash_text("hello")
    assert hash_text("hello") != hash_text("world")
    assert len(hash_text("any text")) == 64
