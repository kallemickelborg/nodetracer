"""Edge-case tests for error handling, schema flexibility, hooks, and resilience."""

from __future__ import annotations

import asyncio
import json
import warnings
from pathlib import Path

import pytest

from nodetracer import trace
from nodetracer.cli import main
from nodetracer.core import Tracer
from nodetracer.exceptions import NodetracerLoadError
from nodetracer.models import Node, NodeStatus, TraceGraph
from nodetracer.serializers import load_trace_json, save_trace_json, trace_from_json
from nodetracer.storage import MemoryStore

# ---------------------------------------------------------------------------
# 1. Storage failure — trace context exits cleanly
# ---------------------------------------------------------------------------


class _FailingStore:
    def save(self, trace: TraceGraph) -> None:
        raise OSError("disk full")

    def load(self, trace_id: str) -> TraceGraph | None:
        return None

    def list_traces(self) -> list[str]:
        return []


def test_storage_failure_does_not_propagate() -> None:
    tracer = Tracer(storage=_FailingStore())

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with (
            tracer.trace("will_fail") as root,
            root.node("step", node_type="tool_call"),
        ):
            pass

    warning_messages = [str(w.message) for w in caught]
    assert any("failed to save trace" in msg for msg in warning_messages)
    assert root.trace.name == "will_fail"
    assert len(root.trace.nodes) == 2


# ---------------------------------------------------------------------------
# 2. Malformed JSON load — raises NodetracerLoadError
# ---------------------------------------------------------------------------


def test_malformed_json_raises_load_error() -> None:
    with pytest.raises(NodetracerLoadError, match="Failed to parse"):
        trace_from_json("{not valid json!!!")


def test_truncated_json_raises_load_error() -> None:
    with pytest.raises(NodetracerLoadError, match="Failed to parse"):
        trace_from_json('{"schema_version": "0.1.0", "trace_id":')


def test_wrong_shape_json_raises_load_error() -> None:
    with pytest.raises(NodetracerLoadError, match="Failed to parse"):
        trace_from_json('"just a string, not an object"')


# ---------------------------------------------------------------------------
# 3. Schema version mismatch — parses with warning
# ---------------------------------------------------------------------------


def test_schema_version_mismatch_warns_but_parses(tmp_path: Path) -> None:
    trace_graph = TraceGraph(name="future_trace")
    node = Node(sequence_number=0, name="step", node_type="custom")
    trace_graph.add_node(node)
    path = save_trace_json(trace_graph, tmp_path / "trace.json")

    raw = json.loads(path.read_text())
    raw["schema_version"] = "0.99.0"
    raw["unknown_future_field"] = "should be ignored"
    path.write_text(json.dumps(raw))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        loaded = load_trace_json(path)

    assert loaded.name == "future_trace"
    assert loaded.schema_version == "0.99.0"
    assert len(loaded.nodes) == 1
    warning_messages = [str(w.message) for w in caught]
    assert any("0.99.0" in msg and "differs" in msg for msg in warning_messages)


# ---------------------------------------------------------------------------
# 4. Non-serializable data — converted to string, not an error
# ---------------------------------------------------------------------------


def test_non_serializable_metadata_converted_to_string() -> None:
    with trace("ns_run") as root, root.node("step", node_type="custom") as step:
        step.metadata(callback=lambda x: x)
        step.input(func=lambda: None)
        step.output(obj=object())

    node = next(n for n in root.trace.nodes.values() if n.name == "step")
    assert "[NON-SERIALIZABLE]" in str(node.metadata["callback"])
    assert "[NON-SERIALIZABLE]" in str(node.input_data["func"])
    assert "[NON-SERIALIZABLE]" in str(node.output_data["obj"])

    json_str = root.trace.model_dump_json()
    json.loads(json_str)


# ---------------------------------------------------------------------------
# 5. CLI on bad file — exit code 1, clear message
# ---------------------------------------------------------------------------


def test_cli_inspect_nonexistent_file(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["inspect", "/tmp/does_not_exist_nodetracer.json"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "error" in captured.err.lower()


def test_cli_inspect_corrupt_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("NOT JSON AT ALL")

    exit_code = main(["inspect", str(bad_file)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "error" in captured.err.lower()


# ---------------------------------------------------------------------------
# 6. Concurrent traces — separate correct TraceGraphs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_traces_are_independent() -> None:
    store = MemoryStore()
    tracer = Tracer(storage=store)

    async def run_trace(name: str) -> TraceGraph:
        async with (
            tracer.trace(name) as root,
            root.node(f"{name}_step", node_type="tool_call"),
        ):
            await asyncio.sleep(0)
        return root.trace

    results = await asyncio.gather(
        run_trace("trace_a"),
        run_trace("trace_b"),
    )

    assert results[0].trace_id != results[1].trace_id
    assert results[0].name == "trace_a"
    assert results[1].name == "trace_b"
    assert len(store.list_traces()) == 2

    a_nodes = [n.name for n in results[0].nodes.values()]
    b_nodes = [n.name for n in results[1].nodes.values()]
    assert "trace_a_step" in a_nodes
    assert "trace_b_step" in b_nodes
    assert "trace_b_step" not in a_nodes
    assert "trace_a_step" not in b_nodes


# ---------------------------------------------------------------------------
# 7. Hook dispatch — correct order and data
# ---------------------------------------------------------------------------


class _RecordingHook:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, str]] = []

    def on_node_started(self, node: Node, trace_id: str) -> None:
        self.events.append(("started", node.name, trace_id))

    def on_node_completed(self, node: Node, trace_id: str) -> None:
        self.events.append(("completed", node.name, trace_id))

    def on_node_failed(self, node: Node, trace_id: str) -> None:
        self.events.append(("failed", node.name, trace_id))

    def on_trace_completed(self, trace: TraceGraph) -> None:
        self.events.append(("trace_completed", trace.name, trace.trace_id))


def test_hook_dispatch_order_and_data() -> None:
    hook = _RecordingHook()
    tracer = Tracer(hooks=[hook])

    with tracer.trace("hooked") as root:
        with root.node("child_a", node_type="tool_call"):
            pass
        with root.node("child_b", node_type="llm_call"):
            pass

    trace_id = root.trace.trace_id
    assert hook.events == [
        ("started", "hooked", trace_id),
        ("started", "child_a", trace_id),
        ("completed", "child_a", trace_id),
        ("started", "child_b", trace_id),
        ("completed", "child_b", trace_id),
        ("completed", "hooked", trace_id),
        ("trace_completed", "hooked", trace_id),
    ]


def test_hook_receives_failed_event_on_error() -> None:
    hook = _RecordingHook()
    tracer = Tracer(hooks=[hook])

    with (
        pytest.raises(ValueError, match="oops"),
        tracer.trace("fail_trace") as root,
        root.node("bad_step", node_type="custom"),
    ):
        raise ValueError("oops")

    failed_events = [e for e in hook.events if e[0] == "failed"]
    failed_names = [e[1] for e in failed_events]
    assert "bad_step" in failed_names


# ---------------------------------------------------------------------------
# 8. Broken hook — trace completes normally
# ---------------------------------------------------------------------------


class _BrokenHook:
    def on_node_started(self, node: Node, trace_id: str) -> None:
        raise RuntimeError("hook crashed!")

    def on_node_completed(self, node: Node, trace_id: str) -> None:
        raise RuntimeError("hook crashed!")

    def on_node_failed(self, node: Node, trace_id: str) -> None:
        raise RuntimeError("hook crashed!")

    def on_trace_completed(self, trace: TraceGraph) -> None:
        raise RuntimeError("hook crashed!")


def test_broken_hook_does_not_crash_trace() -> None:
    tracer = Tracer(hooks=[_BrokenHook()])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with (
            tracer.trace("resilient") as root,
            root.node("step", node_type="tool_call"),
        ):
            pass

    assert root.trace.name == "resilient"
    assert len(root.trace.nodes) == 2
    node = next(n for n in root.trace.nodes.values() if n.name == "step")
    assert node.status == NodeStatus.COMPLETED

    warning_messages = [str(w.message) for w in caught]
    assert any("hook error" in msg for msg in warning_messages)
