# Contributing to logtracer

Thanks for your interest in contributing. logtracer is an open-source project and welcomes contributions of all kinds — bug reports, feature requests, documentation improvements, and code.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/Mickelborg/logtracer.git
cd logtracer
uv venv && source .venv/bin/activate
uv sync --group dev
```

### Verify everything works

```bash
pytest                    # run tests
ruff check .              # lint
ruff format --check .     # format check
```

## How to Contribute

### Reporting Bugs

Open an [issue](https://github.com/Mickelborg/logtracer/issues) with:
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
src/logtracer/
  models/       # Data model (Node, Edge, TraceGraph)
  core/         # Runtime (Tracer, Span, context propagation)
  storage/      # StorageBackend protocol + implementations
  serializers/  # JSON import/export
  renderers/    # Console tree renderer
  cli/          # CLI entry points
tests/          # pytest test suite
examples/       # Runnable agent pattern examples
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
