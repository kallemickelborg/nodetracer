from __future__ import annotations

import nodetracer


def reset_nodetracer_config() -> None:
    """Reset the default tracer between tests."""
    nodetracer._reset_default_tracer()


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_config() -> None:
    reset_nodetracer_config()
