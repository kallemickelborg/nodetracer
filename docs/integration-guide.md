# Integration guide

nodetracer offers three integration levels. Pick the one that fits your project:

| Level            | Effort                              | What you get                     |
| ---------------- | ----------------------------------- | -------------------------------- |
| **Manual**       | `with tracer.trace() / root.node()` | Full control, works everywhere   |
| **Decorator**    | `@trace_node(...)` on functions     | Automatic function-level tracing |
| **Adapter** *(future)* | `pip install nodetracer[framework]` | Auto-instrumentation        |

---

## Level 1: Manual instrumentation

The most flexible approach. You control exactly what gets traced and how.

### Dependency injection (recommended)

Construct a `Tracer` with its own config and storage — no global state.

```python
from nodetracer.core import Tracer, TracerConfig
from nodetracer.storage import FileStore

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

A thin wrapper over the DI API that manages a default global `Tracer`.

```python
import nodetracer

nodetracer.configure(storage="file://./traces")

with nodetracer.trace("quick_run") as root:
    with root.node("step", node_type="tool_call") as step:
        step.input(location="Paris")
        step.output(temp=18)
```

### Async and parallel traces

`Tracer` supports both sync and async context managers. Parallel branches via `asyncio.gather()` automatically fork the trace context through Python's `contextvars`.

```python
import asyncio
from nodetracer.core import Tracer

tracer = Tracer()

async def search(source: str, root):
    async with root.node(f"search_{source}", node_type="tool_call") as step:
        await asyncio.sleep(0.1)
        step.output(source=source, results=["..."])

async def main():
    async with tracer.trace("parallel_agent") as root:
        await asyncio.gather(
            search("web", root),
            search("docs", root),
            search("arxiv", root),
        )

asyncio.run(main())
```

### Recording data on spans

Every span supports the following methods:

| Method                         | Purpose                                         |
| ------------------------------ | ----------------------------------------------- |
| `span.input(**kwargs)`         | Record input data (key-value pairs)             |
| `span.output(**kwargs)`        | Record output data                              |
| `span.metadata(**kwargs)`      | Record arbitrary metadata                       |
| `span.annotate(message)`       | Record developer intent — *why* a decision was made |
| `span.set_status(NodeStatus)`  | Override the automatic status                   |
| `span.link(other, edge_type)`  | Create an explicit edge to another span         |

Non-serializable values are automatically converted to strings with a `[NON-SERIALIZABLE]` marker rather than raising an error.

### Edge types

Edges encode *why* steps connect:

| Edge type       | Meaning                                         |
| --------------- | ----------------------------------------------- |
| `CAUSED_BY`     | A triggered B (control flow)                    |
| `DATA_FLOW`     | Output of A was input to B                      |
| `BRANCHED_FROM` | B is a parallel branch spawned by A             |
| `RETRY_OF`      | B is a retry attempt after A failed             |
| `FALLBACK_OF`   | B ran because A failed (alternative path)       |

```python
from nodetracer.models import EdgeType, NodeStatus

with tracer.trace("recovery") as root:
    with root.node("attempt_1", node_type="tool_call") as a1:
        a1.set_status(NodeStatus.FAILED)

    with root.node("attempt_2", node_type="tool_call") as a2:
        pass

    a1.link(a2, edge_type=EdgeType.RETRY_OF)
```

---

## Level 2: Function decorator

The `@trace_node` decorator wraps a function in a span when a trace is active. When no trace is active, the function runs normally with zero overhead.

```python
from nodetracer import trace
from nodetracer.core import trace_node

@trace_node(node_type="tool_call")
def fetch_weather(location: str) -> dict:
    return {"temp": 18, "condition": "sunny"}

@trace_node(node_type="llm_call")
def classify_intent(query: str) -> str:
    return "weather_lookup"

with trace("agent_run") as root:
    intent = classify_intent("What's the weather?")
    result = fetch_weather("Paris")
```

### How it works

1. `@trace_node` checks for an active trace context (via `contextvars`).
2. If a trace is active, it creates a child span under the current node.
3. If no trace is active, the function runs unmodified.
4. Both sync and async functions are supported.

### Custom span name

By default, the span name is the function name. Override it with the `name` parameter:

```python
@trace_node(name="weather_api_v2", node_type="tool_call")
def fetch_weather(location: str) -> dict:
    ...
```

### Combining with manual spans

Decorators and manual spans compose naturally:

```python
@trace_node(node_type="tool_call")
def search(query: str) -> list[str]:
    return ["result_1", "result_2"]

with trace("mixed") as root:
    with root.node("plan", node_type="decision") as plan:
        plan.annotate("Will search then summarize")

    results = search("latest news")  # auto-traced as child of root

    with root.node("summarize", node_type="llm_call") as llm:
        llm.input(results=results)
        llm.output(summary="Here's what I found...")
```

---

## Level 3: Framework adapters (future)

Framework adapters will provide automatic instrumentation for popular AI agent frameworks. Each adapter will be an optional extra:

```bash
pip install nodetracer[langchain]
pip install nodetracer[crewai]
```

Adapters are not required for the core library to function. See the [adapter implementation guide](#writing-a-framework-adapter) below if you want to contribute one.

---

## Custom storage backends

nodetracer uses a protocol-based storage interface. Any object that implements three methods can serve as a storage backend:

```python
from nodetracer.models import TraceGraph

class MyStorage:
    def save(self, trace: TraceGraph) -> None:
        """Persist a completed trace."""
        ...

    def load(self, trace_id: str) -> TraceGraph | None:
        """Load a trace by ID, or return None if not found."""
        ...

    def list_traces(self) -> list[str]:
        """Return a list of stored trace IDs."""
        ...
```

Pass it to the `Tracer`:

```python
from nodetracer.core import Tracer

tracer = Tracer(storage=MyStorage())
```

### Example: SQLite backend

```python
import json
import sqlite3

from nodetracer.models import TraceGraph
from nodetracer.serializers import trace_from_json, trace_to_json


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS traces (trace_id TEXT PRIMARY KEY, data TEXT)"
        )

    def save(self, trace: TraceGraph) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO traces (trace_id, data) VALUES (?, ?)",
            (trace.trace_id, trace_to_json(trace)),
        )
        self._conn.commit()

    def load(self, trace_id: str) -> TraceGraph | None:
        row = self._conn.execute(
            "SELECT data FROM traces WHERE trace_id = ?", (trace_id,)
        ).fetchone()
        if row is None:
            return None
        return trace_from_json(row[0])

    def list_traces(self) -> list[str]:
        rows = self._conn.execute("SELECT trace_id FROM traces").fetchall()
        return [row[0] for row in rows]
```

---

## Event hooks

The `TracerHook` protocol provides real-time lifecycle events. Implement any subset of the methods — unimplemented ones are no-ops.

```python
from nodetracer.core import Tracer
from nodetracer.models import Node, TraceGraph


class LoggingHook:
    def on_node_started(self, node: Node, trace_id: str) -> None:
        print(f"[STARTED] {node.name}")

    def on_node_completed(self, node: Node, trace_id: str) -> None:
        print(f"[DONE] {node.name} ({node.duration_ms:.0f}ms)")

    def on_trace_completed(self, trace: TraceGraph) -> None:
        print(f"Trace {trace.trace_id}: {len(trace.nodes)} nodes")


tracer = Tracer(hooks=[LoggingHook()])
```

Hook errors never crash the host application. A broken hook emits a warning and the trace continues normally.

---

## What nodetracer does NOT do

Understanding scope is as important as understanding features:

| Not in scope                    | Why                                                                                      | Alternative                                     |
| ------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **LLM API calls**              | nodetracer records structure, not HTTP requests. It doesn't call any model.                | Use your preferred SDK (OpenAI, Anthropic, etc.) |
| **Agent orchestration**         | nodetracer observes execution, it doesn't control it. No routing, planning, or scheduling. | Use LangGraph, CrewAI, Agno, or your own code   |
| **Hosted dashboard / SaaS**    | nodetracer is a local library. There is no cloud service or account.                       | Export traces to your own tooling                |
| **Log aggregation**            | nodetracer captures structured traces, not unstructured log lines.                         | Use structured logging alongside nodetracer      |
| **Metrics / alerting**         | nodetracer captures individual traces, not aggregate metrics.                              | Use Prometheus, Datadog, etc. for metrics        |
| **Automatic code rewriting**   | nodetracer requires explicit instrumentation (context managers or decorators).              | Future auto-instrumentation is on the roadmap    |

---

## Writing a framework adapter

A framework adapter is a thin wrapper that hooks into a framework's lifecycle and creates nodetracer spans. The pattern is always the same:

1. Accept a `Tracer` instance (dependency injection).
2. Subscribe to the framework's lifecycle events (callbacks, hooks, middleware).
3. Create spans with appropriate `node_type` and record inputs/outputs.
4. Handle errors gracefully — adapter failures must not break the host framework.

### Injection point contract

An adapter needs:

| Requirement                     | How to satisfy                                              |
| ------------------------------- | ----------------------------------------------------------- |
| A `Tracer` instance             | Accept via constructor or function parameter                |
| An active trace context         | Call `tracer.trace(name)` or receive a `TraceContext`/`Span` |
| Framework lifecycle events      | Use the framework's callback/hook/middleware system         |
| Node type mapping               | Map framework concepts to `node_type` strings               |

### Skeleton

```python
from nodetracer.core import Tracer
from nodetracer.models import NodeStatus


class ExampleFrameworkAdapter:
    """Adapter for ExampleFramework — maps framework events to nodetracer spans."""

    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    def on_agent_start(self, agent_name: str, input_data: dict) -> None:
        # Framework calls this when an agent starts
        ctx = self._tracer.trace(agent_name)
        ctx.__enter__()
        # Store ctx for later cleanup

    def on_tool_call(self, tool_name: str, args: dict, result: dict) -> None:
        # Framework calls this when a tool is invoked
        # Create a child span under the current trace
        ...

    def on_agent_end(self, output_data: dict) -> None:
        # Framework calls this when the agent finishes
        # Close the trace context
        ...
```

### Guidelines

- **One adapter per framework**, published as an optional extra (`nodetracer[framework_name]`).
- **Never import the framework at the top level** of the adapter module — use lazy imports so the core library doesn't depend on it.
- **Match the framework's naming conventions** for node types (e.g., `llm_call` for LLM invocations, `tool_call` for tool use).
- **Include tests** that mock the framework's lifecycle and verify spans are created correctly.
- **Document the minimum supported framework version** in the adapter's docstring and `pyproject.toml` optional dependency.
