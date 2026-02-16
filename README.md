# logtracer
The visual graph-based Python logging and debugging framework

## Setup with uv

```bash
uv venv
source .venv/bin/activate
uv sync --group dev
```

## CLI

Inspect a saved trace file:

```bash
logtracer inspect path/to/trace.json --verbosity standard
```

Emit machine-readable summary JSON:

```bash
logtracer inspect path/to/trace.json --json
```
