# Contributing to nodetracer

Thanks for your interest in contributing. nodetracer is an open-source project and welcomes contributions of all kinds — bug reports, feature requests, documentation improvements, and code.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/kallemickelborg/nodetracer.git
cd nodetracer
uv venv && source .venv/bin/activate
uv sync --group dev
```

### Verify everything works

```bash
pytest                    # run tests
ruff check .              # lint
ruff format --check .     # format check
```

### Pre-commit (recommended)

Install hooks so ruff runs before each commit and avoids CI failures:

```bash
uv run pre-commit install
```

Then `git commit` will run ruff format and ruff check on staged files; a failing hook aborts the commit. See [pre-commit](https://pre-commit.com/).

## How to Contribute

### Reporting Bugs

Open an [issue](https://github.com/kallemickelborg/nodetracer/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and OS

### Suggesting Features

Open an issue with the `enhancement` label. Describe the use case and why it matters for agent tracing.

### Submitting Code

1. Fork the repository
2. Create a feature branch from `main`: `git checkout -b feat/your-feature`
3. Make your changes
4. Add or update tests for your changes
5. Run the quality checks:
   ```bash
   pytest
   ruff check .
   ruff format .
   ```
6. Commit with a descriptive message: `git commit -m "feat: add X for Y"`
7. Push to your fork: `git push origin feat/your-feature`
8. Open a Pull Request against `main`

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `docs:` — documentation only
- `test:` — adding or updating tests
- `chore:` — maintenance (deps, CI, tooling)

### Code Style

- **Formatting**: `ruff format` (line length 100)
- **Linting**: `ruff check` with rules: E, F, I, UP, B, C4, SIM, RUF
- **Types**: strict typing, no `Any` — use `object` or `unknown` at boundaries
- **Models**: Pydantic v2 `BaseModel` with `ConfigDict(strict=True)`
- **Tests**: `pytest` + `pytest-asyncio`

### Areas Where Help Is Welcome

- **Framework adapters** — integrations for Agno, LangGraph, CrewAI, AutoGen, Swarm
- **Auto-instrumentation** — patching OpenAI/Anthropic SDKs to auto-capture LLM calls
- **Storage backends** — SQLite, PostgreSQL, or other persistence options
- **Documentation** — usage guides, tutorials, API reference
- **Examples** — new agent patterns that exercise the tracing API

## Project Structure

```
src/nodetracer/
  models/       # Data model (Node, Edge, TraceGraph)
  core/         # Runtime (Tracer, Span, context propagation)
  storage/      # StorageBackend protocol + implementations
  serializers/  # JSON import/export
  renderers/    # Console tree renderer
  cli/          # CLI entry points
tests/          # pytest test suite
examples/       # Runnable agent pattern examples
```

## Releasing / versioning

- **Single source of truth:** Version is in `pyproject.toml` only (no `__version__` in code).
- **Merge to main:** The commit that triggers a release must (1) bump the version in `pyproject.toml` to a value **not yet published to PyPI**, and (2) add a matching `## [X.Y.Z]` section in `CHANGELOG.md`. CI will fail on push to main if either is missing, then build and publish to PyPI.
- **One version per release:** Only one version bump per release. If multiple PRs change the version, resolve by taking the higher version or by having a single PR that bumps version and consolidates CHANGELOG entries.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
