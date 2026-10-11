"""Deferred schemas and real ADK runner transitions, without external API access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.genai import types
from pydantic import Field

from tools import mcp_tools as github


def search_repositories(query: str) -> dict:
    """Search repositories by owner or keywords."""
    return {"repositories": []}


def list_issues(owner: str, repo: str) -> dict:
    """List issues in a repository."""
    return {"issues": [{"number": 2, "title": "Test issue"}]}


def create_issue(owner: str, repo: str, title: str) -> dict:
    """Create an issue in a repository."""
    raise AssertionError("Search must never execute a write")


def get_file_contents(owner: str, repo: str, path: str) -> dict:
    """Read file contents from a repository."""
    return {"content": "test"}


@pytest.fixture
def toolset(monkeypatch):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "offline-test-token")
    catalog = [FunctionTool(func=f) for f in (
        search_repositories, list_issues, create_issue, get_file_contents)]
    monkeypatch.setattr(McpToolset, "get_tools", AsyncMock(return_value=catalog))
    return github.get_github_mcp_toolset(defer_loading=True)


@pytest.mark.asyncio
async def test_search_changes_schemas_only_for_its_session(toolset):
    first, other = SimpleNamespace(state={}), SimpleNamespace(state={})
    assert {t.name for t in await toolset.get_tools(first)} == {"search_repositories", "search_github_tools"}
    result = await toolset.search_github_tools("create issue", first)
    assert result["loaded_tools"][0] == "create_issue"
    assert "create_issue" in {t.name for t in await toolset.get_tools(first)}
    assert "create_issue" not in {t.name for t in await toolset.get_tools(other)}
    await toolset.search_github_tools("list issues", first)
    assert first.state[github.GITHUB_LOADED_STATE] == ["list_issues"]
    await toolset.search_github_tools("read file contents", first)
    assert "create_issue" not in {t.name for t in await toolset.get_tools(first)}
    assert "get_file_contents" in {t.name for t in await toolset.get_tools(first)}
    await toolset.search_github_tools("xyzzy", first)
    assert {t.name for t in await toolset.get_tools(first)} == {"search_repositories", "search_github_tools"}


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["", " ", "x" * 201, None])
async def test_invalid_search_preserves_state(toolset, query):
    context = SimpleNamespace(state={github.GITHUB_LOADED_STATE: ["list_issues"]})
    assert (await toolset.search_github_tools(query, context))["status"] == "error"
    assert context.state[github.GITHUB_LOADED_STATE] == ["list_issues"]


@pytest.mark.asyncio
async def test_eager_mode_and_deferred_discovery_failure(toolset, monkeypatch):
    toolset.defer_loading = False
    assert len(await toolset.get_tools()) == 4
    monkeypatch.setattr(McpToolset, "get_tools", AsyncMock(side_effect=RuntimeError("private-token")))
    failed = github.get_github_mcp_toolset(defer_loading=True)
    assert [t.name for t in await failed.get_tools()] == ["get_github_connection_status"]
    result = await failed.search_github_tools("list issues", SimpleNamespace(state={}))
    assert result["status"] == "error"
    assert "private-token" not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", ["create_issue", {"create_issue": True}, [[], "push_files"]])
async def test_unrecognized_state_cannot_expose_extra_tools(toolset, stored):
    context = SimpleNamespace(state={github.GITHUB_LOADED_STATE: stored})
    assert {t.name for t in await toolset.get_tools(context)} == {"search_github_tools", "search_repositories"}


class SearchThenReadModel(BaseLlm):
    """Script the model while ADK itself builds requests and dispatches tools."""

    schemas: list[list[str]] = Field(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        names = sorted(llm_request.tools_dict)
        self.schemas.append(names)
        step = len(self.schemas)
        if step == 1:
            assert "list_issues" not in names
            part = types.Part.from_function_call(name="search_github_tools", args={"query": "list issues"})
        elif step == 2:
            assert "list_issues" in names
            part = types.Part.from_function_call(name="list_issues", args={"owner": "example", "repo": "test"})
        else:
            part = types.Part(text="Found test issue 2.")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


@pytest.mark.asyncio
async def test_adk_runner_search_then_invokes_newly_loaded_tool(toolset):
    model = SearchThenReadModel(model="offline-script")
    agent = LlmAgent(name="search_test", model=model, tools=[toolset])
    sessions = InMemorySessionService()
    await sessions.create_session(app_name="search_test", user_id="test", session_id="first")
    runner = Runner(agent=agent, app_name="search_test", session_service=sessions)
    events = [event async for event in runner.run_async(
        user_id="test", session_id="first",
        new_message=types.Content(role="user", parts=[types.Part(text="List issues")]))]
    calls = [call.name for event in events for call in event.get_function_calls()]
    assert calls == ["search_github_tools", "list_issues"]
    responses = [response for event in events for response in event.get_function_responses()]
    assert responses[-1].response["issues"][0]["number"] == 2
    assert len(model.schemas) == 3
    saved = await sessions.get_session(app_name="search_test", user_id="test", session_id="first")
    assert "list_issues" in saved.state[github.GITHUB_LOADED_STATE]


def test_bonus_factory_uses_deferred_mcp_and_keeps_confirmation(monkeypatch):
    import agent
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "offline-test-token")
    deferred = agent.create_agent_with_tool_search()
    eager = agent.create_agent()
    assert next(t for t in deferred.tools if isinstance(t, McpToolset)).defer_loading is True
    assert next(t for t in eager.tools if isinstance(t, McpToolset)).defer_loading is False
    assert "Wait for a clear affirmative" in deferred.instruction
