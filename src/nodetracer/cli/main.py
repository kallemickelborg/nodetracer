"""Command line interface for nodetracer."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from .inspect_cmd import VerbosityArg, run_inspect


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nodetracer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a trace JSON file")
    inspect_parser.add_argument("trace_file", type=Path, help="Path to trace JSON file")
    inspect_parser.add_argument(
        "--verbosity",
        choices=["minimal", "standard", "full"],
        default="standard",
        help="Console render verbosity",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable summary JSON instead of text output",
    )
    inspect_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output file path for --json summary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        return run_inspect(
            args.trace_file,
            cast(VerbosityArg, args.verbosity),
            as_json=args.json,
            output_path=args.output,
        )

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
