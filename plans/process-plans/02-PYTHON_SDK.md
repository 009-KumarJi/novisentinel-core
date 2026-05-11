# 02 — Python SDK

**Polish the existing `sdk/python/` package and publish to PyPI.**

The SDK already works (`Client`, `AsyncClient`, `scan`, `scan_batch`). This plan covers the polish + publish, plus a few ergonomics the current version is missing.

**Effort:** ~3 days, one engineer.
**Depends on:** F-101 (README) for marketing copy parity.
**Gate to:** F-505 (examples — they import the SDK).

---

## F-201 — SDK API audit

**Phase:** Pre-launch · **Effort:** S · **Depends on:** —

**Goal:** The SDK's surface is small, consistent, and well-typed. No `dict` returns, no missing docstrings, no untyped `Any`.

### Tasks

- [ ] **T1.** Read `sdk/python/novisentinel/client.py` and `models.py`. Compare against the BE's `ScanRequest` / `ScanResponse` Pydantic models in `app/api/scan.py`. Confirm every BE field has a corresponding SDK field.
- [ ] **T2.** Add docstrings to every public method. Format: 1-line summary, blank line, Args, Returns, Raises, Example.
- [ ] **T3.** Add `ScanResult` convenience properties:
  - `.has_pii: bool`
  - `.has_injection: bool`
  - `.has_secrets: bool`
  - `.has_toxicity: bool`
  - `.detections_by_type(type: str) -> list[Detection]`
- [ ] **T4.** Add `ScanError` exception subclasses:
  - `ScanError` (base)
  - `AuthError(ScanError)` — 401/403
  - `RateLimitError(ScanError)` — 429, carries `retry_after`
  - `ServiceUnavailableError(ScanError)` — 503
  - `ValidationError(ScanError)` — 422
- [ ] **T5.** Map HTTP errors to these exceptions in both `Client` and `AsyncClient`. Today both call `resp.raise_for_status()` which only raises generic `httpx.HTTPStatusError` — wrap it.
- [ ] **T6.** Add a `timeout` parameter to `Client.__init__` (defaults to 30s — already there as `_TIMEOUT`, but should be configurable).
- [ ] **T7.** Add `Client.health() -> bool` — calls `GET /healthz` and returns True/False without raising.

### Files

| Action | Path |
|---|---|
| edit | `sdk/python/novisentinel/client.py` |
| edit | `sdk/python/novisentinel/models.py` |
| create | `sdk/python/novisentinel/exceptions.py` |
| edit | `sdk/python/novisentinel/__init__.py` (export the new exceptions) |

### Acceptance

- Every public method has a docstring.
- `mypy --strict sdk/python/novisentinel/` passes (or `pyright` if you prefer).
- Calling `.scan()` against an unreachable server raises `ServiceUnavailableError`, not a generic httpx error.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 [x] T5 — 2026-05-11

---

## F-202 — SDK tests

**Phase:** Pre-launch · **Effort:** S · **Depends on:** F-201

**Goal:** The SDK has its own test suite. Independent of the BE's tests.

### Tasks

- [ ] **T1.** Create `sdk/python/tests/`. Add `__init__.py` and `conftest.py`.
- [ ] **T2.** Use `respx` to mock `httpx`. No live BE required.
- [ ] **T3.** Test `Client.scan()`:
  - Happy path: 200 + valid ScanResponse → returns ScanResult.
  - 401 → raises `AuthError`.
  - 429 with `Retry-After: 12` → raises `RateLimitError(retry_after=12)`.
  - 503 → raises `ServiceUnavailableError`.
  - 422 → raises `ValidationError`.
- [ ] **T4.** Test `Client.scan_batch()`: same matrix, batch shape.
- [ ] **T5.** Test `AsyncClient` symmetrically.
- [ ] **T6.** Test the convenience properties (`.has_pii`, `.detections_by_type`).
- [ ] **T7.** Add `pytest`, `pytest-asyncio`, `respx` to `sdk/python/pyproject.toml` `[project.optional-dependencies].test`.
- [ ] **T8.** Wire into CI (F-103). New job `sdk-test`: `cd sdk/python && pip install -e .[test] && pytest`.

### Files

| Action | Path |
|---|---|
| create | `sdk/python/tests/__init__.py`, `conftest.py`, `test_client.py`, `test_async_client.py`, `test_models.py` |
| edit | `sdk/python/pyproject.toml` (test deps) |
| edit | `.github/workflows/ci.yml` (new job) |

### Acceptance

- `cd sdk/python && pytest` runs green.
- CI runs both `tests/` (BE) and `sdk/python/tests/` (SDK) on every PR.
- Coverage on the SDK is ≥ 90% of lines.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 [x] T5 [x] T6 [x] T7 [x] T8 — 2026-05-11

---

## F-203 — PyPI publish

**Phase:** Pre-launch · **Effort:** XS · **Depends on:** F-201, F-202

**Goal:** `pip install novisentinel` works on a fresh machine.

### Tasks

- [ ] **T1.** Confirm the package name `novisentinel` is available on PyPI. Search: `https://pypi.org/project/novisentinel/`. If taken, fall back to `novisentinel-client` or `novisentinel-sdk`. Update `pyproject.toml` accordingly. **Do this check first — everything downstream depends on the name.**
- [ ] **T2.** Polish `pyproject.toml`:
  - Add `[project.classifiers]` — Python versions, license, intended audience, topic.
  - Add `[project.urls]` — Homepage, Repository, Issues, Documentation, Changelog.
  - Add `keywords = ["llm", "ai-safety", "pii", "prompt-injection", "guardrails"]`.
  - Bump version to `0.1.0` (it's already 0.1.0; verify).
- [ ] **T3.** Create `sdk/python/README.md` — a slim version of the main README focused on SDK usage. PyPI displays this.
- [ ] **T4.** Confirm `LICENSE` is in the package: add `license-files = ["LICENSE"]` to `[project]`.
- [ ] **T5.** Build locally: `cd sdk/python && python -m build`. Confirm `dist/novisentinel-0.1.0-py3-none-any.whl` and `dist/novisentinel-0.1.0.tar.gz` are created.
- [ ] **T6.** Inspect the wheel: `unzip -l dist/novisentinel-0.1.0-py3-none-any.whl`. Confirm it contains: `novisentinel/__init__.py`, `client.py`, `models.py`, `exceptions.py`, `LICENSE`.
- [ ] **T7.** Publish to TestPyPI first: `python -m twine upload --repository testpypi dist/*`. Install from TestPyPI in a fresh venv: `pip install --index-url https://test.pypi.org/simple/ novisentinel`. Run a real scan. Confirm it works.
- [ ] **T8.** Publish to real PyPI: `python -m twine upload dist/*`.
- [ ] **T9.** Verify: in a fresh venv on a different machine, `pip install novisentinel` followed by `python -c "import novisentinel; print(novisentinel.__version__)"` returns `0.1.0`.
- [ ] **T10.** Set up trusted-publisher OIDC for the GitHub repo so future releases publish from CI without manual `twine upload`. See [`pypi-publish` GitHub Action docs](https://docs.pypi.org/trusted-publishers/).
- [ ] **T11.** Add a `release.yml` workflow that triggers on `tag: v*` and publishes the SDK if the version matches.

### Files

| Action | Path |
|---|---|
| edit | `sdk/python/pyproject.toml` |
| create | `sdk/python/README.md` |
| create | `.github/workflows/release.yml` |

### Acceptance

- `pip install novisentinel` works on a fresh Python 3.11 venv on macOS, Linux, and Windows.
- `https://pypi.org/project/novisentinel/` renders the package's README and metadata correctly.
- Tagging `v0.1.1` and pushing triggers an automated PyPI publish.

### Status

- [x] T1 [x] T2 — 2026-05-11 (name confirmed available, pyproject.toml polished) [ ] T3 [ ] T4 [ ] T5 [ ] T6 [ ] T7 [ ] T8 [ ] T9 [ ] T10 [ ] T11 (manual: build + publish)

---

## F-204 — Retries with backoff

**Phase:** Pre-launch · **Effort:** XS · **Depends on:** F-201

**Goal:** Transient 5xx errors retry with exponential backoff. Users running NoviSentinel locally + occasionally restarting Docker shouldn't lose work to a 503 mid-scan.

### Tasks

- [ ] **T1.** Add a `retries: int = 3` parameter to `Client.__init__`.
- [ ] **T2.** Wrap the `httpx.post()` call in a retry loop:
  - Retry on 502/503/504 and `httpx.ConnectError`.
  - Do NOT retry on 4xx (those are user errors).
  - Exponential backoff: 0.5s, 1s, 2s.
  - Respect `Retry-After` header on 429.
- [ ] **T3.** Same for `AsyncClient` using `asyncio.sleep`.
- [ ] **T4.** Test: BE returns 503 twice then 200 → SDK should return the 200 result silently.
- [ ] **T5.** Test: BE returns 503 four times → SDK should raise `ServiceUnavailableError` after exhausting retries.

### Acceptance

- A flaky BE doesn't break SDK callers.
- Retry budget is configurable; default of 3 is sensible.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 [x] T5 — 2026-05-11 (implemented in client.py + test_client.py)

---

## F-205 — Streaming `scan_iter` (deferred)

**Phase:** Post-launch · **Effort:** M · **Depends on:** F-203

**Goal:** Allow the SDK to scan very long texts in chunks and yield detections as they arrive. Useful for streaming LLM responses.

This is a substantial API addition and is deferred until post-launch unless a community user specifically asks for it. Capture the idea here so it doesn't get lost.

### Tasks

- [ ] **T1.** Design note: write `plans/notes/F-205.md` covering: chunking strategy (window size? overlap?), how to dedupe detections at chunk boundaries, sync vs async API shape.
- [ ] **T2.** Don't build until at least one external user asks.

### Status

- [ ] T1 [ ] T2

---

## Done condition for this plan

Phase complete when F-201, F-202, F-203, F-204 are all `[x]`. F-205 sits frozen until demanded.

When this plan is done:
- The PyPI page is live.
- The SDK has tests, types, errors, retries.
- The launch can reference `pip install novisentinel` as a real artifact.
