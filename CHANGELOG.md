# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.1] - 2026-02-26

### Added

- **Renderer improvements**: `nodetracer inspect` now shows edge labels inline (`[retry of X]`, `[fallback of X]`, `[branched from X]`, `[→ X]`). Standard verbosity shows annotations and errors without full I/O. Full verbosity truncates large input/output (200 chars) with `[truncated]` marker.

## [0.3.0] - 2026-02-25

### Added

- **HTTP auto-instrumentation**: Zero-boilerplate tracing of HTTP requests via `pip install nodetracer[http]` and `instrument_http()`. Patches requests, httpx (sync + async), and aiohttp. When a trace is active, every HTTP request creates a child span with `method`, `url`, `status_code`, `duration_ms`, and `error` (if failed). Optional `url_filter` and `exclude_urls` for redaction and URL filtering.

## [0.2.1] - 2026-02-25

### Added

- **Auto-capturing `@trace_node` decorator**: New `capture_args` and `capture_return` parameters on `@trace_node()`. When `capture_args=True`, function arguments are automatically recorded as span input data (`self` is excluded for methods). When `capture_return=True`, the return value is recorded as span output data. Dict returns are spread into output fields; scalar returns use the `return_value` key.

### Fixed

- **Build**: Exclude non-library files from source distribution (sdist was incorrectly including unrelated project files).

## [0.1.0] - 2026-02-24

Initial release.

### Added

- **Core tracing API**: `Tracer`, `TraceContext`, `Span` with sync and async context manager support.
- **Data model**: `Node`, `Edge`, `TraceGraph` with Pydantic validation and JSON serialization.
- **Edge types**: `CAUSED_BY`, `BRANCHED_FROM`, `RETRY_OF`, `FALLBACK_OF` for representing agent execution relationships.
- **Dependency injection**: Construct `Tracer` with explicit `TracerConfig` and `StorageBackend`, or use the convenience `configure()` / `trace()` API.
- **Event hook protocol**: `TracerHook` with `on_node_started`, `on_node_completed`, `on_node_failed`, `on_trace_completed` lifecycle events. Zero overhead when no hooks are registered.
- **Storage backends**: `MemoryStore` (default) and `FileStore` (JSON files on disk). Custom backends via `StorageBackend` protocol.
- **Error handling**: Runtime tracing errors never crash the host application (OpenTelemetry-style contract). Configuration errors fail fast.
- **Schema flexibility**: Forward-compatible reader (`extra="ignore"` on all models). Version mismatch emits a warning, does not error.
- **CLI**: `nodetracer inspect <file>` renders a trace as a rich terminal tree.
- **Decorator**: `@trace_node(...)` for automatic function-level tracing.
- **Packaging**: `py.typed` marker (PEP 561), complete `__all__` exports, typed inline annotations.
- **CI/CD**: GitHub Actions test matrix (Python 3.11/3.12/3.13) and release workflow with PyPI trusted publishing.

[0.3.1]: https://pypi.org/project/nodetracer/0.3.1/
[0.3.0]: https://pypi.org/project/nodetracer/0.3.0/
[0.2.1]: https://pypi.org/project/nodetracer/0.2.1/
[0.1.0]: https://pypi.org/project/nodetracer/0.1.0/
