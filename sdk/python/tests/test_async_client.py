import httpx
import pytest
import respx

from novisentinel import AsyncClient, AuthError, RateLimitError, ServiceUnavailableError, ValidationError

from .conftest import API_KEY, API_URL, BATCH_RESPONSE, SCAN_RESPONSE

pytestmark = pytest.mark.asyncio


@pytest.fixture
def client():
    return AsyncClient(api_key=API_KEY, base_url=API_URL, retries=0)


@pytest.fixture
def client_with_retries():
    return AsyncClient(api_key=API_KEY, base_url=API_URL, retries=2)


# ── scan() ────────────────────────────────────────────────────────────────────


class TestAsyncScan:
    @respx.mock
    async def test_happy_path(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(200, json=SCAN_RESPONSE))
        result = await client.scan("My SSN is 123-45-6789")
        assert result.action == "block"
        assert result.has_pii is True

    @respx.mock
    async def test_401_raises_auth_error(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(401))
        with pytest.raises(AuthError):
            await client.scan("test")

    @respx.mock
    async def test_429_raises_rate_limit_error_with_retry_after(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(429, headers={"retry-after": "12"}))
        with pytest.raises(RateLimitError) as exc_info:
            await client.scan("test")
        assert exc_info.value.retry_after == 12.0

    @respx.mock
    async def test_503_raises_service_unavailable(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(503))
        with pytest.raises(ServiceUnavailableError):
            await client.scan("test")

    @respx.mock
    async def test_422_raises_validation_error(self, client):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(422, json={"detail": "bad"}))
        with pytest.raises(ValidationError):
            await client.scan("test")

    @respx.mock
    async def test_retry_succeeds_on_third_attempt(self, client_with_retries):
        route = respx.post(f"{API_URL}/v1/scan")
        route.side_effect = [
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json=SCAN_RESPONSE),
        ]
        result = await client_with_retries.scan("test")
        assert result.action == "block"

    @respx.mock
    async def test_retry_exhausted_raises_service_unavailable(self, client_with_retries):
        respx.post(f"{API_URL}/v1/scan").mock(return_value=httpx.Response(503))
        with pytest.raises(ServiceUnavailableError):
            await client_with_retries.scan("test")


# ── scan_batch() ───────────────────────────────────────────────────────────────


class TestAsyncScanBatch:
    @respx.mock
    async def test_happy_path(self, client):
        respx.post(f"{API_URL}/v1/scan/batch").mock(return_value=httpx.Response(200, json=BATCH_RESPONSE))
        results = await client.scan_batch(["text1", "text2"])
        assert len(results) == 2

    @respx.mock
    async def test_403_raises_auth_error(self, client):
        respx.post(f"{API_URL}/v1/scan/batch").mock(return_value=httpx.Response(403))
        with pytest.raises(AuthError):
            await client.scan_batch(["text"])


# ── health() ──────────────────────────────────────────────────────────────────


class TestAsyncHealth:
    @respx.mock
    async def test_returns_true_on_200(self, client):
        respx.get(f"{API_URL}/healthz").mock(return_value=httpx.Response(200))
        assert await client.health() is True

    @respx.mock
    async def test_returns_false_on_503(self, client):
        respx.get(f"{API_URL}/healthz").mock(return_value=httpx.Response(503))
        assert await client.health() is False
