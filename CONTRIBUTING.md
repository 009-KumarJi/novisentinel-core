# Contributing to NoviSentinel

Thanks for your interest in contributing! NoviSentinel is an AI safety firewall and every contribution helps make LLM applications more secure.

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone the repo**

```bash
git clone https://github.com/009-KumarJi/novi-sentinel.git
cd novi-sentinel
```

2. **Start infrastructure** (PostgreSQL + Redis)

```bash
docker compose up postgres redis -d
```

3. **Set up Python environment**

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

4. **Install git hooks** (enforces commit conventions and code quality)

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
```

5. **Configure environment**

```bash
cp .env.example .env
# The defaults work for local development
```

6. **Run the API**

```bash
uvicorn app.main:app --reload --port 8000
```

The API is live at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### Running Tests

```bash
pytest tests/ -v
```

All 54 tests run without Docker — they mock database and Redis dependencies.

---

## How to Contribute

### Reporting Bugs

- Open an issue using the **Bug Report** template
- Include: steps to reproduce, expected vs actual behavior, environment details
- For **security bugs**, see [SECURITY.md](SECURITY.md) instead

### Suggesting Features

- Open an issue using the **Feature Request** template
- Explain the use case and why it benefits the project

### Submitting Code

1. **Fork** the repository
2. **Create a branch** from `main` (see [Branch Naming](#branch-naming) below)
3. **Make your changes** — follow the guidelines below
4. **Add/update tests** for any new functionality
5. **Run the test suite** to make sure nothing breaks:
   ```bash
   pytest tests/ -v
   ```
6. **Commit** using the conventions below
7. **Push** and open a **Pull Request** against `main`

---

## Git Convention

### Commit Format

```
<type>(<scope>): <summary>

<body>          ← optional
<footer>        ← optional
```

### Official Types

| Type       | Meaning                  | Version Impact |
|------------|--------------------------|----------------|
| `feat`     | New capability           | minor          |
| `fix`      | Bug fix                  | patch          |
| `perf`     | Performance optimization | patch          |
| `refactor` | Internal restructuring   | —              |
| `security` | Security-related changes | patch          |
| `ai`       | AI/LLM pipeline changes  | minor          |
| `infra`    | Infra/platform/devops    | —              |
| `docs`     | Documentation            | —              |
| `test`     | Testing                  | —              |
| `build`    | Build/dependency updates | —              |
| `ci`       | CI/CD workflows          | —              |
| `chore`    | Misc maintenance         | —              |

### Recommended Scopes

#### Core

```
core, engine, pipeline, runtime, scheduler, worker, queue
```

#### AI / LLM

```
agent, rag, vector, embedding, inference, guardrails, memory, prompt
```

#### Security / Monitoring

```
scanner, audit, policy, sandbox, detection, threat, auth, rbac
```

#### Platform / Infra

```
api, db, cache, redis, docker, k8s, observability, metrics, logging
```

### Example Commits

```
ai(rag): add hybrid semantic retrieval pipeline
security(scanner): detect unsafe shell execution patterns
perf(vector): reduce embedding search latency by 40%
infra(observability): add structured tracing support
refactor(worker): simplify async retry orchestration
feat(api)!: remove legacy v1 execution endpoints        ← breaking change
```

### Writing Good Commit Subjects

| ✅ Do | ❌ Don't |
|-------|---------|
| `fix: rate limiter check-then-add race condition` | `fix: fixed bug` |
| `security(scanner): detect unsafe shell execution` | `security: updates` |
| `perf: aggregate stats with SQL instead of Python` | `perf: make it faster` |
| Use imperative mood ("add", "fix", "remove") | Use past tense ("added", "fixed") |
| Keep under 72 characters | Write a paragraph |
| Start lowercase after the colon | Capitalize the subject |

### NEVER Use These Words in Commits

```
fixes, updates, temp, misc, working, final, wip
```

### Commit Body & Footer

Use the body to explain **what** and **why** (not how — the code shows how):

```
security(auth): reject startup with default master key in production

The default 'dev-master-key' is publicly documented in .env.example
and README. Running production with this key is a critical security
risk. The app now raises RuntimeError on startup if ENVIRONMENT != dev
and the key hasn't been changed.

Closes #42
```

**Footer keywords:**
- `Closes #123` — auto-closes the linked issue on merge
- `Breaking-Change: <description>` — flags a breaking change
- `Co-authored-by: Name <email>` — credit co-authors

### Breaking Changes

Use `!` after the scope:

```
feat(api)!: remove legacy v1 execution endpoints
```

### Multi-Change Commits

Split into separate commits. Don't do:

```
❌  feat: add IBAN detector, fix webhook bug, update README
```

Instead:

```
✅  feat(pii): add IBAN detection
✅  fix(webhook): prevent duplicate delivery on retry
✅  docs: add IBAN to detection table in README
```

---

## Branch Naming

```
<type>/<short-feature-name>
```

| Example | Area |
|---------|------|
| `feat/rag-memory` | New feature |
| `fix/redis-timeout` | Bug fix |
| `security/prompt-injection-check` | Security hardening |
| `perf/vector-cache` | Performance |
| `infra/grafana-setup` | Infrastructure |
| `ai/streaming-agent` | AI pipeline |

---

## Pull Request Conventions

### PR Title

Same format as commits — this becomes the squash merge commit message:

```
feat(agent): add multi-step execution planner
fix(cache): prevent stale inference state
security(policy): validate unsafe tool execution
```

### PR Description

Every PR must include: **Summary**, **Changes**, **Why**, **Testing**, **Performance Impact**, **Risks**. See the PR template for the full format.

### PR Size Guidelines

| Size | Lines Changed | Review Time |
|------|--------------|-------------|
| 🟢 Small | < 100 | Minutes |
| 🟡 Medium | 100–300 | Same day |
| 🔴 Large | 300+ | Split it up |

### Squash Merge Strategy

We use **squash merge** on GitHub. Your final history becomes:

```
feat(agent): add streaming execution support
fix(cache): prevent stale inference state
security(policy): validate unsafe tool execution
```

Extremely clean OSS history.

---

## Semantic Versioning

```
MAJOR.MINOR.PATCH   →   v1.4.2
```

| Change | Version Impact |
|--------|----------------|
| `feat` | minor (1.x.0) |
| `fix`, `perf`, `security` | patch (1.0.x) |
| Breaking change (`!`) | major (x.0.0) |

---

## Code Guidelines

### Project Structure

```
app/
├── api/          # FastAPI route handlers
├── core/         # Scanner orchestrator, webhook delivery
├── detectors/    # Detection modules (PII, injection, secrets, toxicity)
├── db/           # SQLAlchemy models, async session
└── config.py     # Pydantic settings

sdk/python/       # Python SDK (pip install novisentinel)
tests/            # pytest test suite
```

### Writing Detectors

All detectors inherit from `BaseDetector` in `app/detectors/base.py`:

```python
class BaseDetector(ABC):
    @abstractmethod
    def scan(self, text: str, config: dict | None = None) -> list[DetectionResult]:
        """Synchronous scan."""

    async def scan_async(self, text: str, config: dict | None = None) -> list[DetectionResult]:
        """Async scan — override for ML-based detectors."""
        return self.scan(text, config)
```

If you're adding a new detector:

1. Create `app/detectors/your_detector.py`
2. Implement the `BaseDetector` interface
3. Register it in `app/core/scanner.py`
4. Add tests in `tests/test_your_detector.py`

### Style

- **Python**: Follow PEP 8. Use type hints. Use `async`/`await` for I/O.
- **Commits**: Use the Git Convention documented above.
- **Tests**: Every new feature or bug fix should include tests.

### What Makes a Good PR

- Solves one problem (don't bundle unrelated changes)
- Includes tests
- Updates documentation if the user-facing API changes
- Has a clear description of *what* and *why*

---

## Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to enforce code quality and commit conventions automatically. See `.pre-commit-config.yaml` for the full configuration.

**What runs on each commit:**
- Commit message format validation (Conventional Commits)
- Trailing whitespace and EOF fixes
- No secrets or credentials in code
- No `.env` files committed
- Python linting (Ruff)
- YAML/TOML syntax validation

**What runs on each push:**
- Full test suite (`pytest tests/ -v`)

---

## Code of Conduct

By participating, you agree to our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?

Open a [Discussion](https://github.com/009-KumarJi/novi-sentinel/discussions) or reach out via an issue. We're happy to help you get started!
