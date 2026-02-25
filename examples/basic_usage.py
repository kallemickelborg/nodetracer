"""Basic usage example using the convenience API."""

from __future__ import annotations

from pathlib import Path

from nodetracer import configure, trace
from nodetracer.renderers import render_trace
from nodetracer.serializers import save_trace_json


def main() -> None:
    output_dir = Path("artifacts")
    output_dir.mkdir(exist_ok=True)
    configure(storage="memory")

    with trace("agent_run", metadata={"agent_version": "0.1.0"}) as root:
        with root.node("plan", node_type="decision") as planner:
            planner.input(query="What is the weather in San Francisco?")
            planner.output(chosen_tool="weather_api")
            planner.annotate("Classified user intent as weather lookup")

        with root.node("weather_api_call", node_type="tool_call") as api_call:
            api_call.input(location="San Francisco")
            api_call.output(temperature_f=62, condition="foggy")

    trace_path = save_trace_json(root.trace, output_dir / f"{root.trace.trace_id}.json")
    print(render_trace(root.trace, verbosity="full"))
    print(f"Trace file saved to: {trace_path}")


if __name__ == "__main__":
    main()
