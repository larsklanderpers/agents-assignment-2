"""Direct GitHub MCP configuration required by Part 2 of the assignment."""

import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
MCP_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "mcp_servers.json"
GITHUB_TOOLS = ["search_repositories", "list_issues", "get_issue", "create_issue", "get_file_contents"]
GITHUB_LOADED_STATE = "github_loaded_tools"


def search_github_tools(query: str, catalog: list[BaseTool]) -> list[BaseTool]:
    """Rank discovered, allowed GitHub tools by name and description; return at most two."""
    words = {word.rstrip("s") for word in re.findall(r"[a-z]+", query.lower())}
    words -= {"a", "an", "the", "my", "github", "tool", "to", "for", "and", "in"}
    ranked = []
    for tool in catalog:
        names = {word.rstrip("s") for word in tool.name.split("_")}
        description = {word.rstrip("s") for word in re.findall(r"[a-z]+", tool.description.lower())}
        score = 4 * len(words & names) + len(words & description)
        if score:
            ranked.append((score, tool))
    ranked.sort(key=lambda item: (-item[0], item[1].name))
    # Do not expose create_issue merely because a list-issues query includes "issue".
    return [tool for score, tool in ranked if score == ranked[0][0]][:2] if ranked else []


def handle_github_tool_error(tool: BaseTool, args: dict, tool_context: ToolContext,
                             error: Exception) -> Optional[dict]:
    """Return safe GitHub call errors to the agent instead of aborting its turn."""
    if tool.name not in GITHUB_TOOLS:
        return None
    detail = str(error).lower()
    if "issues has been disabled" in detail or "issues are disabled" in detail:
        return {
            "status": "error", "code": "issues_disabled",
            "message": "GitHub rejected the request because Issues are disabled for this repository. Enable Issues in the repository's Settings > General > Features, then ask to retry. No issue was created by this rejected request.",
        }
    if "not found" in detail:
        code = "not_found"
        message = "GitHub could not find or grant access to the requested resource. Check the exact owner/repository name and token access."
    elif "unauthorized" in detail or "bad credentials" in detail or "authentication" in detail:
        code = "authentication_error"
        message = "GitHub authentication failed. Check the local token and restart ADK after replacing it."
    elif "rate limit" in detail:
        code = "rate_limited"
        message = "GitHub rate limited the request. Wait before trying again."
    elif "forbidden" in detail or "permission" in detail or "accessible by" in detail:
        code = "permission_denied"
        message = "GitHub denied access. Check that the token has the required repository and issue permissions."
    else:
        code = "github_tool_error"
        message = "The GitHub tool did not finish successfully. Check the MCP connection and repository access."
    if tool.name == "create_issue":
        message += " The creation result is uncertain. List issues and check the exact title before any retry; do not automatically repeat the write."
    return {"status": "error", "code": code, "message": message}


def get_github_connection_status() -> dict:
    """Explain a failed GitHub connection and the local steps needed to restore it."""
    return {
        "status": "error",
        "message": "GitHub MCP could not connect. Check Node.js and npx, internet access, and GITHUB_PERSONAL_ACCESS_TOKEN in your local .env, then restart ADK. Google Tasks is still available.",
    }


class GitHubMcpToolset(McpToolset):
    """Add context-aware schema deferral and safe discovery to ADK 1.18's McpToolset.

    ADK 1.18 has no native defer_loading argument. This subclass implements it
    with get_tools: metadata is discovered locally, but only selected schemas
    reach the model. Selections live in session state, never on this shared object.
    """

    def __init__(self, *, defer_loading: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.defer_loading = defer_loading
        self._catalog_tools = None

    async def search_github_tools(self, query: str, tool_context: ToolContext) -> dict:
        """Find GitHub tools by capability and load up to two for the next model step.

        Args:
            query: Capability keywords, such as create issue, list issues, or read file.

        Returns:
            Matching names and brief descriptions, or an actionable error. This
            only selects tool schemas; it does not execute GitHub actions.
        """
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            return {"status": "error", "message": "Use 1 to 200 characters describing the GitHub capability you need."}
        catalog = await self._discover_tools(tool_context)
        if self._connection_failed:
            return get_github_connection_status()
        matches = search_github_tools(query, catalog)
        # Replace the prior selection rather than growing the schema set forever.
        tool_context.state[GITHUB_LOADED_STATE] = [tool.name for tool in matches]
        return {
            "status": "success", "loaded_tools": [tool.name for tool in matches],
            "matches": [{"name": tool.name, "description": tool.description[:300]} for tool in matches],
            "message": "Matching tools are available on the next model step. Writes still require confirmation." if matches else "No matching supported tool. Try repository, issue, or file keywords.",
        }

    async def _discover_tools(self, readonly_context=None) -> list[BaseTool]:
        if getattr(self, "_connection_failed", False):
            return [FunctionTool(func=get_github_connection_status)]
        if self._catalog_tools is not None:
            return self._catalog_tools
        try:
            self._catalog_tools = await super().get_tools(readonly_context)
            self._connection_failed = False
            return self._catalog_tools
        except Exception:
            # Repeated failed startup attempts would delay every subsequent Tasks request.
            self._connection_failed = True
            return [FunctionTool(func=get_github_connection_status)]

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> list[BaseTool]:
        catalog = await self._discover_tools(readonly_context)
        if not self.defer_loading or self._connection_failed:
            return catalog
        selected = set()
        if readonly_context is not None:
            stored = readonly_context.state.get(GITHUB_LOADED_STATE, [])
            if isinstance(stored, list):
                selected = {name for name in stored if isinstance(name, str) and name in GITHUB_TOOLS}
        selected.add("search_repositories")
        return [FunctionTool(func=self.search_github_tools), *[tool for tool in catalog if tool.name in selected]]


def github_token_is_configured() -> bool:
    """Check for a token without displaying it or accepting the example placeholders."""
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "").strip()
    return bool(token) and not any(marker in token.lower() for marker in ("your_token", "ghp_xxx", "replace_me"))


def get_github_mcp_toolset(*, defer_loading: bool = False) -> McpToolset:
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
        defer_loading=defer_loading,
    )


def get_github_mcp_toolset_deferred() -> McpToolset:
    """Configure on-demand GitHub schemas while retaining direct McpToolset integration."""
    return get_github_mcp_toolset(defer_loading=True)


def load_mcp_config() -> dict:
    """Read the optional starter configuration and resolve environment placeholders."""
    with MCP_CONFIG_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)
    environment = config.get("mcpServers", {}).get("github", {}).get("env", {})
    for key, value in environment.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            environment[key] = os.getenv(value[2:-1], "")
    return config
