"""Optional: expose the classifier as MCP tools so agents (Claude Desktop, Claude Code, etc.) can call it.

Install: pip install "mcp>=2"
Run:     python mcp_server.py        (stdio transport)
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from rfx.pipeline import run_dir, sample_leads

mcp = MCPServer("rfx-classifier")


@mcp.tool()
def list_sample_leads() -> list[str]:
    """List bundled sample lead packets."""
    return list(sample_leads())


@mcp.tool()
def classify_lead_folder(path: str) -> dict:
    """Classify a lead packet folder (metadata.json + .txt/.pdf/.docx files).

    Accepts an absolute path or the name of a bundled sample lead.
    """
    folder = sample_leads().get(path) or Path(path)
    _, selection, result = run_dir(folder)
    return {**result.to_payload(), "flags": result.flags,
            "document_scores": [asdict(s) for s in selection.scores]}


if __name__ == "__main__":
    mcp.run()
