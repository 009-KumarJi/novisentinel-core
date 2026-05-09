import hashlib
import secrets
import string
from uuid import UUID


def _master_key_uuid(master_key: str) -> UUID:
    digest = hashlib.sha256(b"master:" + master_key.encode()).digest()
    return UUID(bytes=digest[:16], version=4)


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, prefix, sha256_hash)."""
    alphabet = string.ascii_letters + string.digits
    raw = "nvs_" + "".join(secrets.choice(alphabet) for _ in range(40))
    prefix = raw[:8]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, key_hash


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
