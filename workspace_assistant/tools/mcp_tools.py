"""Direct GitHub MCP configuration required by Part 2 of the assignment."""

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
MCP_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "mcp_servers.json"
GITHUB_TOOLS = ["search_repositories", "list_issues", "get_issue", "create_issue", "get_file_contents"]


def get_github_connection_status() -> dict:
    """Explain a failed GitHub connection and the local steps needed to restore it."""
    return {
        "status": "error",
        "message": "GitHub MCP could not connect. Check Node.js and npx, internet access, and GITHUB_PERSONAL_ACCESS_TOKEN in your local .env, then restart ADK. Google Tasks is still available.",
    }


class GitHubMcpToolset(McpToolset):
    """Keep Tasks usable if GitHub tool discovery fails before the model can respond."""

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> list[BaseTool]:
        if getattr(self, "_connection_failed", False):
            return [FunctionTool(func=get_github_connection_status)]
        try:
            return await super().get_tools(readonly_context)
        except Exception:
            # Repeated failed startup attempts would delay every subsequent Tasks request.
            self._connection_failed = True
            return [FunctionTool(func=get_github_connection_status)]


def github_token_is_configured() -> bool:
    """Check for a token without displaying it or accepting the example placeholders."""
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "").strip()
    return bool(token) and not any(marker in token.lower() for marker in ("your_token", "ghp_xxx", "replace_me"))


def get_github_mcp_toolset() -> McpToolset:
    """Configure the assignment's GitHub server; connection starts when ADK requests tools.

    Returns:
        McpToolset exposing repository search, issue queries/creation, and file reading.

    Raises:
        ValueError: A real GITHUB_PERSONAL_ACCESS_TOKEN has not been configured locally.
    """
    if not github_token_is_configured():
        raise ValueError("Set GITHUB_PERSONAL_ACCESS_TOKEN in workspace_assistant/.env to enable GitHub MCP.")

    server_params = StdioServerParameters(
        command="npx.cmd" if os.name == "nt" else "npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"].strip()},
    )
    return GitHubMcpToolset(
        connection_params=StdioConnectionParams(server_params=server_params, timeout=60),
        tool_filter=GITHUB_TOOLS,
    )


def load_mcp_config() -> dict:
    """Read the optional starter configuration and resolve environment placeholders."""
    with MCP_CONFIG_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)
    environment = config.get("mcpServers", {}).get("github", {}).get("env", {})
    for key, value in environment.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            environment[key] = os.getenv(value[2:-1], "")
    return config
