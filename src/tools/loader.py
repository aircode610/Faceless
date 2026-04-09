"""
"A man selects the tools a man needs."

Loads real MCP servers as LangChain tools using langchain-mcp-adapters.
Each supported MCP name maps to a stdio-based MCP server spec that gets
launched on demand and exposed as a set of LangChain tool objects.

Supported today:
  - "github" -> @modelcontextprotocol/server-github (needs GITHUB_PERSONAL_ACCESS_TOKEN)
  - "search" -> tavily-mcp                         (needs TAVILY_API_KEY)

Unknown MCP names are silently skipped so selecting e.g. "slack" in the
bootstrap does not break the execution pipeline.
"""

from __future__ import annotations

import asyncio
import json
import os

from src.config import AGENT_CONFIG_PATH

# Map of MCP name -> MultiServerMCPClient server spec.
# This is the single source of truth for which MCPs Faceless supports —
# both the bootstrap form and the runtime tool loader read from here.
MCP_SERVER_SPECS: dict[str, dict] = {
    "github": {
        "description": (
            "Read/write GitHub repos, pull requests, issues, and reviews. "
            "Use for any task that involves inspecting code changes, PR "
            "metadata, file contents, or posting review comments."
        ),
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "transport": "stdio",
        "env_passthrough": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    },
    "search": {
        "description": (
            "Web search via Tavily. Use to look up current information, "
            "CVE databases, library documentation, or anything outside the "
            "model's training data."
        ),
        "command": "npx",
        "args": ["-y", "tavily-mcp@latest"],
        "transport": "stdio",
        "env_passthrough": ["TAVILY_API_KEY"],
    },
}


def get_mcp_catalog() -> list[dict]:
    """
    Return the catalog of supported MCPs in the shape the UI expects:
      [{"name": ..., "description": ...}, ...]
    """
    return [
        {"name": name, "description": spec["description"]}
        for name, spec in MCP_SERVER_SPECS.items()
    ]


def _build_server_config(selected: list[str]) -> dict:
    """Build MultiServerMCPClient config dict for the selected MCPs."""
    config: dict = {}
    for name in selected:
        spec = MCP_SERVER_SPECS.get(name)
        if not spec:
            continue

        # Check that required env vars exist. If missing, skip this server
        # with a warning — we don't want to crash the whole task over a
        # missing token.
        env_keys = spec.get("env_passthrough", [])
        missing = [k for k in env_keys if not os.environ.get(k)]
        if missing:
            print(
                f"[mcp] Skipping '{name}' MCP — missing env vars: {', '.join(missing)}"
            )
            continue

        entry = {
            "command": spec["command"],
            "args": list(spec["args"]),
            "transport": spec["transport"],
        }
        # IMPORTANT: MCP's stdio transport REPLACES the subprocess env when
        # you pass `env=...` — it does not merge with the parent process
        # environment. That means we must include PATH, HOME, NODE_PATH,
        # etc. explicitly, or npx-launched servers will misbehave.
        #
        # We merge the full parent env first, then layer in the required
        # secrets. This way the subprocess gets a full functional
        # environment (PATH resolves npx, HOME lets npm find its caches,
        # proxies/TLS certs work) PLUS the credentials it needs.
        merged_env = dict(os.environ)
        for k in env_keys:
            merged_env[k] = os.environ[k]
        entry["env"] = merged_env
        config[name] = entry
    return config


async def _load_tools_async(selected: list[str]) -> list:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    config = _build_server_config(selected)
    if not config:
        return []
    client = MultiServerMCPClient(config)
    try:
        tools = await client.get_tools()
        return tools
    except Exception as e:
        print(f"[mcp] Failed to load MCP tools: {e}")
        return []


def load_tools_for_agent() -> list:
    """
    Read agent_config.json and return LangChain tools for each selected MCP
    that has a concrete implementation. Runs the async loader inside a
    fresh event loop so this stays callable from sync code.
    """
    if not os.path.exists(AGENT_CONFIG_PATH):
        return []

    with open(AGENT_CONFIG_PATH) as f:
        config = json.load(f)

    selected = config.get("selected_mcps", [])
    if not selected:
        return []

    try:
        # asyncio.run() creates a new loop — safe because orchestrator nodes
        # run in FastAPI's threadpool (no existing loop on that thread).
        return asyncio.run(_load_tools_async(selected))
    except RuntimeError:
        # Fallback: a loop is already running (e.g. async context). Use
        # a separate thread to run the coroutine in its own loop.
        import threading
        result: list = []

        def _runner():
            nonlocal result
            result = asyncio.run(_load_tools_async(selected))

        t = threading.Thread(target=_runner)
        t.start()
        t.join()
        return result


def get_available_mcps() -> list[str]:
    """Names of MCPs that have a concrete server spec registered."""
    return list(MCP_SERVER_SPECS.keys())


def get_mcps_with_credentials() -> list[str]:
    """MCPs whose required env vars are actually set in the environment."""
    result = []
    for name, spec in MCP_SERVER_SPECS.items():
        env_keys = spec.get("env_passthrough", [])
        if all(os.environ.get(k) for k in env_keys):
            result.append(name)
    return result
