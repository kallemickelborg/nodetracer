# logtracer

**The tracing library for agentic software.**
Record, inspect, and debug AI agent execution — across any framework, any model, any scale.

[Documentation](#usage) &bull; [Examples](#agent-pattern-examples) &bull; [Quick Start](#quick-start) &bull; [Contributing](#contributing)

---

## What is logtracer?

AI agents plan, branch, retry, delegate, and fail — often invisibly. logtracer makes every step of that execution visible by recording it as a **temporal directed graph** that you can inspect, compare, and debug.

| Layer | What it provides |
|---|---|
| **Capture** | Context managers, decorators, and DI-based tracing that works with sync, async, and parallel execution |
| **Data Model** | Typed nodes, edges, annotations, and metadata — capturing *what* happened, *why*, and *how long* |
| **Storage** | Pluggable backends (memory, file, custom) with a protocol-based interface |
| **Inspect** | CLI and Rich console renderer for terminal-based trace exploration |

logtracer is **not** a platform, a SaaS, or a dashboard. It's a Python library you `pip install` and instrument in 3 lines. No accounts. No API keys. No vendor lock-in.

## Why logtracer?

Agentic software introduces a fundamental observability gap. Traditional tools weren't built for it:

| Tool | The gap |
|---|---|
| **LangSmith, LangFuse, Arize Phoenix** | Tied to specific frameworks or require SaaS accounts. Not agnostic. |
| **OpenTelemetry, Datadog** | Built for microservices. Flat trace timelines lose the branching, decision-making structure of agents. |
| **Print statements** | The current reality for most agent developers. No structure, no context, doesn't scale. |

logtracer fills this gap with a graph-native approach purpose-built for agent reasoning:

- **Nodes** = discrete steps (LLM calls, tool invocations, decisions, retrieval, sub-agent delegations)
- **Edges** = typed relationships (*why* steps connect: causation, data flow, retry, fallback, branch)
- **Annotations** = developer intent (the *reasoning* behind decisions, not just inputs and outputs)
- **Time** = first-class dimension (start/end timestamps on every node for performance analysis)

## Quick Start

Instrument a tool-calling agent and get a structured trace in ~10 lines:

```python
from logtracer.core import Tracer, TracerConfig
from logtracer.storage import FileStore

tracer = Tracer(
    config=TracerConfig(),
    storage=FileStore("./traces"),
)

with tracer.trace("weather_agent") as root:
    with root.node("classify_intent", node_type="llm_call") as step:
        step.input(query="What's the weather in Paris?")
        step.output(intent="weather_lookup", confidence=0.95)
        step.annotate("High confidence — routing to weather tool")

    with root.node("weather_api", node_type="tool_call") as tool:
        tool.input(location="Paris")
        tool.output(temperature_c=18, condition="partly cloudy")
```

Then inspect it from the terminal:

```bash
logtracer inspect traces/<trace-id>.json
```

```
Trace: weather_agent (0ms)
├── [llm_call] classify_intent (0ms) ✓
│   └── annotation: "High confidence — routing to weather tool"
└── [tool_call] weather_api (0ms) ✓
    ├── input: {'location': 'Paris'}
    └── output: {'temperature_c': 18, 'condition': 'partly cloudy'}
```

## Key Features

### Framework-agnostic

Works with [Agno](https://github.com/agno-agi/agno), LangGraph, CrewAI, AutoGen, Swarm, [Dify](https://github.com/langgenius/dify), bare OpenAI/Anthropic SDKs, or no framework at all. The core has zero opinions about your stack.

### Dependency injection

`Tracer` is constructed with its own config and storage — no global state. Frameworks inject it like any other service. A thin convenience layer exists for quick scripts.

```python
# DI path (production)
tracer = Tracer(config=TracerConfig(max_output_size=10_000), storage=FileStore("./traces"))

# Convenience path (prototyping)
import logtracer
logtracer.configure(storage="file://./traces")
```

### Async-native

Built on Python's `contextvars` from day one. Parallel branches via `asyncio.gather()` or `TaskGroup` automatically fork the trace context — each branch gets its own lane in the graph.

```python
async with tracer.trace("parallel_search") as root:
    results = await asyncio.gather(
        search("web"),    # traced as parallel node
        search("docs"),   # traced as parallel node
        search("arxiv"),  # traced as parallel node
    )
```

### Rich edge semantics

Edges aren't just "A → B". They encode the *type* of relationship:

| Edge type | Meaning |
|---|---|
| `CAUSED_BY` | A triggered B (control flow) |
| `DATA_FLOW` | Output of A was input to B |
| `BRANCHED_FROM` | B is a parallel branch spawned by A |
| `RETRY_OF` | B is a retry attempt after A failed |
| `FALLBACK_OF` | B ran because A failed (alternative path) |

### Developer annotations

Auto-captured inputs and outputs are useful but insufficient. `annotate()` records **why** the agent made a decision — the information that actually drives improvement.

```python
with root.node("route", node_type="decision") as node:
    node.annotate("User query matched retrieval pattern with 0.94 confidence")
    node.annotate("Skipping web search — cached results are fresh (<5min)")
```

## Install

```bash
pip install logtracer
```

Development setup:

```bash
uv venv && source .venv/bin/activate
uv sync --group dev
```

## Usage

### DI API (recommended for production and framework integration)

```python
from logtracer.core import Tracer, TracerConfig
from logtracer.storage import FileStore

tracer = Tracer(
    config=TracerConfig(max_output_size=10_000),
    storage=FileStore("./traces"),
)

with tracer.trace("my_agent") as root:
    with root.node("plan", node_type="decision") as plan:
        plan.input(query="What should I do?")
        plan.output(action="search")
        plan.annotate("Query matched search pattern")

    with root.node("search", node_type="tool_call") as search:
        search.input(query="latest news")
        search.output(results=["article_1", "article_2"])
```

### Convenience API (quick scripts)

```python
import logtracer

logtracer.configure(storage="file://./traces")

with logtracer.trace("quick_run") as root:
    with root.node("step", node_type="tool_call") as step:
        step.input(location="Paris")
        step.output(temp=18)
```

### Function decorator

```python
from logtracer import trace
from logtracer.core import trace_node

@trace_node(node_type="tool_call")
def fetch_weather(location: str) -> dict:
    return {"temp": 18}

with trace("run") as root:
    fetch_weather("Paris")  # automatically traced as a child node
```

## CLI

```bash
logtracer inspect traces/abc123.json                         # summary + tree
logtracer inspect traces/abc123.json --verbosity full        # with input/output data
logtracer inspect traces/abc123.json --json                  # machine-readable summary
logtracer inspect traces/abc123.json --json --output s.json  # write to file
```

## Agent Pattern Examples

Runnable scripts in `examples/` validate the library against real agent patterns:

| Example | Pattern | What it validates |
|---|---|---|
| `01_sequential_tool_calling.py` | Query → classify → tool → synthesize | Nesting, annotations, JSON roundtrip |
| `02_parallel_execution.py` | Fan-out via `asyncio.gather()` | Context propagation across async tasks |
| `03_retry_and_fallback.py` | Fail → retry → fail → fallback | `RETRY_OF` / `FALLBACK_OF` edges, mixed status |
| `04_multi_agent_handoff.py` | Router delegates to specialist | Nested sub-agent spans, deep nesting |

```bash
python examples/01_sequential_tool_calling.py
python examples/02_parallel_execution.py
python examples/03_retry_and_fallback.py
python examples/04_multi_agent_handoff.py
```

## Architecture

```
src/logtracer/
  __init__.py     # Convenience API (configure, trace, trace_node)
  models/         # Node, Edge, TraceGraph, enums (Pydantic v2)
  core/           # Tracer, Span, TracerConfig, context propagation, decorators
  storage/        # StorageBackend protocol, MemoryStore, FileStore
  serializers/    # JSON import/export
  renderers/      # Rich console tree renderer
  cli/            # CLI entry points (inspect)
```

| Component | Responsibility |
|---|---|
| **models/** | Data model — `Node`, `Edge`, `TraceGraph`. Pydantic v2, strict typing, JSON-serializable. |
| **core/** | Runtime — `Tracer` (DI-constructed), `Span` (lifecycle), `TracerConfig`, context propagation via `contextvars`. |
| **storage/** | Persistence — `StorageBackend` protocol with `MemoryStore` and `FileStore` implementations. Pluggable. |
| **serializers/** | JSON import/export for trace data. The contract between capture and any downstream tool. |
| **renderers/** | Output — `Rich`-based console tree renderer with minimal/standard/full verbosity. |
| **cli/** | Terminal tooling — `logtracer inspect` for trace exploration. |

## Roadmap

### Done

- [x] Core capture engine (nodes, edges, context propagation, async-native)
- [x] DI-based `Tracer` with `TracerConfig` (Pydantic v2)
- [x] Pluggable storage (`MemoryStore`, `FileStore`, custom backends via protocol)
- [x] CLI `inspect` with text, JSON, and file output
- [x] Rich console tree renderer (minimal / standard / full verbosity)
- [x] JSON serialization with versioned schema (`v0.1.0`)
- [x] Agent validation examples (sequential, parallel, retry/fallback, multi-agent handoff)

### Next

- [ ] **PyPI release** — publish `logtracer` as an installable package (`pip install logtracer`)
- [ ] **Framework adapters** — Agno, LangGraph, CrewAI, AutoGen, Swarm
- [ ] **Auto-instrumentation** — patch OpenAI / Anthropic SDKs to auto-capture LLM calls
- [ ] **Trace comparison** — load two traces, align by node name/type, highlight differences
- [ ] **Interactive trace viewer** — browser-based temporal swimlane visualization
- [ ] **Production hardening** — sampling, redaction, size limits, async export

### Future

- [ ] SQLite / PostgreSQL storage backends
- [ ] Event hooks (`on("node.completed")` for custom alerting)
- [ ] Streaming LLM response capture
- [ ] Human-in-the-loop tracing (pause/resume)
- [ ] OpenTelemetry export bridge

## Installing from Source

logtracer is not yet published on PyPI. To install from the repository:

```bash
pip install git+https://github.com/Mickelborg/logtracer.git
```

Or clone and install locally:

```bash
git clone https://github.com/Mickelborg/logtracer.git
cd logtracer
pip install -e .
```

## Contributing

Contributions are welcome — whether it's bug reports, feature ideas, documentation, or code. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

### Quick setup

```bash
git clone https://github.com/Mickelborg/logtracer.git
cd logtracer
uv venv && source .venv/bin/activate
uv sync --group dev
pytest && ruff check .
```

### Areas where help is most needed

- **Framework adapters** — integrations for Agno, LangGraph, CrewAI, AutoGen
- **Auto-instrumentation** — patching LLM SDKs to auto-capture calls
- **Storage backends** — SQLite, PostgreSQL, or cloud storage
- **Documentation** — usage guides, tutorials, API reference
- **Examples** — new agent patterns that exercise the tracing API

## License

[MIT](LICENSE)
