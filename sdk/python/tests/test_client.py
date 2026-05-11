import httpx
import pytest
import respx

from novisentinel import AuthError, Client, RateLimitError, ServiceUnavailableError, ValidationError

from .conftest import API_KEY, API_URL, BATCH_RESPONSE, SCAN_RESPONSE


@pytest.fixture
def client():
    return Client(api_key=API_KEY, base_url=API_URL, retries=0)


@pytest.fixture
def client_with_retries():
    return Client(api_key=API_KEY, base_url=API_URL, retries=2)


# ── scan() ────────────────────────────────────────────────────────────────────


class TestScan:
    @respx.mock
    def test_happy_path(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(200, json=SCAN_RESPONSE))
        result = client.scan("My SSN is 123-45-6789")
        assert result.action == "block"
        assert result.scan_id == "scan_abc123"
        assert result.has_pii is True

    @respx.mock
    def test_401_raises_auth_error(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(401))
        with pytest.raises(AuthError):
            client.scan("test")

    @respx.mock
    def test_403_raises_auth_error(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(403))
        with pytest.raises(AuthError):
            client.scan("test")

    @respx.mock
    def test_429_raises_rate_limit_error_with_retry_after(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(429, headers={"retry-after": "12"}))
        with pytest.raises(RateLimitError) as exc_info:
            client.scan("test")
        assert exc_info.value.retry_after == 12.0

    @respx.mock
    def test_429_without_retry_after_header(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(429))
        with pytest.raises(RateLimitError) as exc_info:
            client.scan("test")
        assert exc_info.value.retry_after is None

    @respx.mock
    def test_503_raises_service_unavailable(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(503))
        with pytest.raises(ServiceUnavailableError):
            client.scan("test")

    @respx.mock
    def test_422_raises_validation_error(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(422, json={"detail": "bad request"}))
        with pytest.raises(ValidationError):
            client.scan("test")

    @respx.mock
    def test_retry_succeeds_on_third_attempt(self, client_with_retries):
        route = respx.post(f"{API_URL}/v1/scan")
        route.side_effect = [
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json=SCAN_RESPONSE),
        ]
        result = client_with_retries.scan("test")
        assert result.action == "block"

    @respx.mock
    def test_retry_exhausted_raises_service_unavailable(self, client_with_retries):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(503))
        with pytest.raises(ServiceUnavailableError):
            client_with_retries.scan("test")

    def test_connect_error_raises_service_unavailable(self, client):
        with respx.mock:
            respx.post(f"{API_URL}/v1/scan").mock(side_effect=httpx.ConnectError("refused"))
            with pytest.raises(ServiceUnavailableError):
                client.scan("test")


# ── scan_batch() ───────────────────────────────────────────────────────────────


class TestScanBatch:
    @respx.mock
    def test_happy_path(self, client):
        respx.post(f"{API_URL}/v1/scan/batch").mock(return_value=httpx.Response(200, json=BATCH_RESPONSE))
        results = client.scan_batch(["text1", "text2"])
        assert len(results) == 2
        assert results[0].action == "block"
        assert results[1].action == "allow"

    @respx.mock
    def test_401_raises_auth_error(self, client):
        respx.post(f"{API_URL}/v1/scan/batch").mock(return_value=httpx.Response(401))
        with pytest.raises(AuthError):
            client.scan_batch(["text"])


# ── health() ──────────────────────────────────────────────────────────────────


class TestHealth:
    @respx.mock
    def test_returns_true_on_200(self, client):
        respx.get(f"{API_URL}/healthz").mock(return_value=httpx.Response(200))
        assert client.health() is True

    @respx.mock
    def test_returns_false_on_503(self, client):
        respx.get(f"{API_URL}/healthz").mock(return_value=httpx.Response(503))
        assert client.health() is False

    def test_returns_false_on_connection_error(self, client):
        with respx.mock:
            respx.get(f"{API_URL}/healthz").mock(side_effect=httpx.ConnectError("refused"))
            assert client.health() is False
