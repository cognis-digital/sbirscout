"""SBIRSCOUT MCP server — exposes digest as an MCP tool for Cognis.Studio.

This module is optional; it requires the ``cognis_core`` package which ships
separately.  Importing sbirscout itself never triggers this file.
"""
from __future__ import annotations

try:
    from cognis_core.mcp import build_mcp_server  # type: ignore[import]
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "cognis_core is not installed — install it to use the MCP server: "
        "pip install cognis-core"
    ) from _exc

from sbirscout.core import digest, SOURCES  # noqa: E402 — after optional import guard
from sbirscout import TOOL_NAME  # noqa: E402

_DESCRIPTION = (
    "SBIR/STTR topic discovery — DSIP + SBIR.gov + NIH digest with bid scoring. "
    "Supported sources: " + ", ".join(SOURCES.keys())
)

run_mcp_server = build_mcp_server(
    tool_name=TOOL_NAME,
    description=_DESCRIPTION,
    scan_fn=digest,
)

if __name__ == "__main__":  # pragma: no cover
    run_mcp_server()
