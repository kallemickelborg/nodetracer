"""View subcommand — starts a local HTTP server exposing trace data as REST."""

from __future__ import annotations

import json
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

from ..storage import FileStore


class TraceAPIHandler(BaseHTTPRequestHandler):
    """Serves trace data as JSON REST endpoints with CORS for local dev."""

    store: ClassVar[FileStore]

    def do_GET(self) -> None:
        if self.path == "/api/traces":
            self._handle_list_traces()
        elif self.path.startswith("/api/traces/"):
            trace_id = self.path[len("/api/traces/"):]
            self._handle_get_trace(trace_id)
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_OPTIONS(self) -> None:
        self._send_cors_preflight()

    def _handle_list_traces(self) -> None:
        file_ids = self.store.list_traces()
        summaries = []
        for fid in file_ids:
            try:
                trace = self.store.load(fid)
                if trace is None:
                    continue
                summaries.append({
                    "id": fid,
                    "trace_id": trace.trace_id,
                    "name": trace.name,
                    "duration_ms": trace.duration_ms,
                    "start_time": trace.start_time.isoformat() if trace.start_time else None,
                    "node_count": len(trace.nodes),
                    "edge_count": len(trace.edges),
                })
            except Exception:
                summaries.append({"id": fid, "name": fid, "error": "Failed to load"})
        summaries.sort(key=lambda s: s.get("start_time") or "", reverse=True)
        self._send_json(HTTPStatus.OK, summaries)

    def _handle_get_trace(self, trace_id: str) -> None:
        trace = self.store.load(trace_id)
        if trace is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Trace {trace_id} not found"})
            return
        body = trace.model_dump_json(indent=2)
        self._send_response(HTTPStatus.OK, body.encode("utf-8"), "application/json")

    def _send_json(self, status: HTTPStatus, data: object) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self._send_response(status, body, "application/json")

    def _send_response(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_preflight(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._add_cors_headers()
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def _add_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: object) -> None:
        print(f"[nodetracer] {self.address_string()} - {format % args}")


def run_view(
    directory: Path,
    port: int = 8765,
    *,
    open_browser: bool = True,
) -> int:
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        return 1

    store = FileStore(str(directory))
    TraceAPIHandler.store = store

    server_address = ("127.0.0.1", port)
    try:
        httpd = HTTPServer(server_address, TraceAPIHandler)
    except OSError as exc:
        print(f"Error: could not start server on port {port}: {exc}", file=sys.stderr)
        print(f"Try a different port: nodetracer view {directory} --port {port + 1}", file=sys.stderr)
        return 1

    url = f"http://127.0.0.1:{port}"
    print(f"[nodetracer] Trace API server running at {url}")
    print(f"[nodetracer] Serving traces from: {directory.resolve()}")
    print(f"[nodetracer] Endpoints:")
    print(f"  GET /api/traces      — list all traces")
    print(f"  GET /api/traces/{{id}} — get full trace by ID")
    print()

    trace_count = len(store.list_traces())
    print(f"[nodetracer] Found {trace_count} trace(s)")
    print(f"[nodetracer] Press Ctrl+C to stop")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[nodetracer] Shutting down...")
        httpd.shutdown()
    return 0
