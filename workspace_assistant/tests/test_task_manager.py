"""Offline behavior tests: no OAuth, Gemini calls, or GitHub subprocesses."""

import importlib
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httplib2
import pytest
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from googleapiclient.errors import HttpError

from tools import tasks_tools as tasks
from tools import mcp_tools as github


@pytest.fixture
def service(monkeypatch):
    client = MagicMock()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(tasks, "get_tasks_service", factory)
    return client, factory


def test_create_formats_date_and_preserves_notes(service):
    client, _ = service
    client.tasks.return_value.insert.return_value.execute.return_value = {
        "id": "t1", "title": "Review PR", "status": "needsAction"
    }
    result = tasks.create_task(" Review PR ", notes="Read the diff", due_date="2026-10-16")
    assert result["status"] == "success"
    assert result["task"]["id"] == "t1"
    client.tasks.return_value.insert.assert_called_once_with(
        tasklist="@default",
        body={"title": "Review PR", "notes": "Read the diff", "due": "2026-10-16T00:00:00.000Z"},
    )


@pytest.mark.parametrize("title,due", [
    (" ", ""), ("x" * 1025, ""), ("Task", "2026-02-30"),
    ("Task", "Friday"), ("Task", "20261016"),
    ("Task", "2026-10-16T14:00:00Z"),
])
def test_invalid_create_never_authenticates(service, title, due):
    _, factory = service
    result = tasks.create_task(title, due_date=due)
    assert result["status"] == "error"
    assert result["code"] == "invalid_input"
    factory.assert_not_called()


def test_notes_limit_is_checked_before_auth(service):
    _, factory = service
    assert tasks.create_task("Task", notes="x" * 8193)["code"] == "invalid_input"
    factory.assert_not_called()


def test_update_only_patches_requested_fields(service):
    client, _ = service
    client.tasks.return_value.patch.return_value.execute.return_value = {"id": "t1"}
    assert tasks.update_task("t1", title="New title")["status"] == "success"
    client.tasks.return_value.patch.assert_called_once_with(
        tasklist="@default", task="t1", body={"title": "New title"}
    )
    client.tasks.return_value.update.assert_not_called()


def test_update_can_clear_notes_and_due_date(service):
    client, _ = service
    client.tasks.return_value.patch.return_value.execute.return_value = {"id": "t1"}
    tasks.update_task("t1", notes="", due_date="")
    assert client.tasks.return_value.patch.call_args.kwargs["body"] == {"notes": "", "due": None}


def test_empty_update_never_authenticates(service):
    _, factory = service
    assert tasks.update_task("t1")["code"] == "invalid_input"
    factory.assert_not_called()


def test_complete_uses_patch(service):
    client, _ = service
    client.tasks.return_value.patch.return_value.execute.return_value = {
        "id": "t1", "status": "completed"
    }
    result = tasks.complete_task("t1", task_list_id="list2")
    assert result["task"]["status"] == "completed"
    client.tasks.return_value.patch.assert_called_once_with(
        tasklist="list2", task="t1", body={"status": "completed"}
    )


def test_delete_handles_empty_api_response(service):
    client, _ = service
    client.tasks.return_value.delete.return_value.execute.return_value = ""
    result = tasks.delete_task("t1")
    assert result == {"status": "success", "task_id": "t1", "message": "Task deleted."}
    client.tasks.return_value.delete.assert_called_once_with(tasklist="@default", task="t1")


@pytest.mark.parametrize("tool", [tasks.complete_task, tasks.delete_task])
def test_missing_task_id_never_authenticates(service, tool):
    _, factory = service
    assert tool(" ")["code"] == "invalid_input"
    factory.assert_not_called()


def test_list_exposes_pagination_and_completed_items(service):
    client, _ = service
    client.tasks.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "t1", "title": "Done", "status": "completed"}],
        "nextPageToken": "page3",
    }
    result = tasks.list_tasks(show_completed=True, page_token="page2", max_results=10)
    assert result["next_page_token"] == "page3"
    assert result["tasks"][0]["id"] == "t1"
    kwargs = client.tasks.return_value.list.call_args.kwargs
    assert kwargs["showCompleted"] is True
    assert kwargs["showHidden"] is True
    assert kwargs["showDeleted"] is False
    assert kwargs["pageToken"] == "page2"
    assert kwargs["maxResults"] == 10


def test_empty_list_is_success(service):
    client, _ = service
    client.tasks.return_value.list.return_value.execute.return_value = {}
    assert tasks.list_tasks() == {"status": "success", "tasks": [], "next_page_token": ""}


@pytest.mark.parametrize("limit", [0, 101, True])
def test_invalid_page_size_never_authenticates(service, limit):
    _, factory = service
    assert tasks.list_tasks(max_results=limit)["code"] == "invalid_input"
    factory.assert_not_called()


def test_list_task_lists_returns_real_ids(service):
    client, _ = service
    client.tasklists.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "list2", "title": "Work"}], "nextPageToken": "next"
    }
    result = tasks.list_task_lists()
    assert result["task_lists"] == [{"id": "list2", "title": "Work"}]
    assert result["next_page_token"] == "next"


@pytest.mark.parametrize("status,code", [
    (401, "authentication_error"), (403, "permission_denied"),
    (404, "not_found"), (429, "rate_limited"), (503, "service_unavailable"),
])
def test_api_errors_are_actionable_and_redacted(service, status, code):
    client, _ = service
    error = HttpError(httplib2.Response({"status": status}), b'{"error":{"message":"secret-value"}}')
    client.tasks.return_value.list.return_value.execute.side_effect = error
    result = tasks.list_tasks()
    assert result["status"] == "error"
    assert result["code"] == code
    assert "secret-value" not in str(result)
    assert result["message"]


def test_missing_credentials_has_setup_guidance(service):
    _, factory = service
    factory.side_effect = FileNotFoundError("sensitive-local-path")
    result = tasks.list_tasks()
    assert result["code"] == "missing_credentials"
    assert "credentials.json" in result["message"]
    assert "sensitive-local-path" not in str(result)


def test_write_timeout_is_not_retried(service):
    client, _ = service
    request = client.tasks.return_value.insert.return_value
    request.execute.side_effect = TimeoutError("private error")
    result = tasks.create_task("Task")
    assert result["status"] == "error"
    assert "before retrying" in result["message"]
    request.execute.assert_called_once_with()


def test_adk_can_build_every_function_schema():
    for function in tasks.tasks_tools:
        declaration = FunctionTool(func=function)._get_declaration()
        assert declaration.name == function.__name__


@pytest.mark.parametrize("token", ["", "ghp_your_token_here", "ghp_xxx", "your_token_here"])
def test_mcp_rejects_missing_or_example_tokens(monkeypatch, token):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", token)
    assert not github.github_token_is_configured()
    with pytest.raises(ValueError, match="GITHUB_PERSONAL_ACCESS_TOKEN"):
        github.get_github_mcp_toolset()


def test_mcp_configuration_does_not_start_a_process(monkeypatch):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test-token-not-valid")
    factory = MagicMock()
    monkeypatch.setattr(github, "GitHubMcpToolset", factory)
    github.get_github_mcp_toolset()
    args = factory.call_args.kwargs
    params = args["connection_params"].server_params
    assert Path(params.command).name == ("npx.cmd" if os.name == "nt" else "npx")
    assert params.args == ["-y", "@modelcontextprotocol/server-github"]
    assert params.env["GITHUB_PERSONAL_ACCESS_TOKEN"] == "test-token-not-valid"
    assert {"search_repositories", "list_issues", "create_issue"} <= set(args["tool_filter"])
    assert "push_files" not in args["tool_filter"]


def test_agent_loads_tasks_without_github_credentials(monkeypatch):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    module = importlib.import_module("agent")
    instance = module.create_agent()
    assert instance.name == "workspace_assistant"
    assert len(instance.instruction) > 100
    assert not any(isinstance(tool, McpToolset) for tool in instance.tools)
    assert "not configured" in instance.instruction
    assert module.root_agent is not None
    assert module.get_current_date()["status"] == "success"


def test_agent_includes_real_mcp_toolset_when_configured(monkeypatch):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test-token-not-valid")
    module = importlib.import_module("agent")
    assert any(isinstance(tool, McpToolset) for tool in module.create_agent().tools)


def test_package_import_used_by_adk_web(monkeypatch):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-c", "from workspace_assistant.agent import root_agent; print(root_agent.name)"],
        cwd=root, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "workspace_assistant" in result.stdout


@pytest.mark.asyncio
async def test_failed_github_discovery_leaves_a_friendly_tool(monkeypatch):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test-token-not-valid")
    connect = AsyncMock(side_effect=FileNotFoundError("secret-value"))
    monkeypatch.setattr(McpToolset, "get_tools", connect)
    toolset = github.get_github_mcp_toolset()
    discovered = await toolset.get_tools()
    assert [tool.name for tool in discovered] == ["get_github_connection_status"]
    result = await discovered[0].run_async(args={}, tool_context=None)
    assert result["status"] == "error"
    assert "secret-value" not in str(result)
    assert "Node.js" in result["message"]
    assert "restart" in result["message"]
    await toolset.get_tools()
    connect.assert_awaited_once()


def test_disabled_issues_error_returns_actionable_result_without_exception_details():
    tool = MagicMock()
    tool.name = "create_issue"
    result = github.handle_github_tool_error(
        tool, {}, None,
        RuntimeError("Failed to create issue: Issues has been disabled in this repository. secret-token"),
    )
    assert result["code"] == "issues_disabled"
    assert "Settings > General > Features" in result["message"]
    assert "No issue was created" in result["message"]
    assert "secret-token" not in str(result)


def test_uncertain_github_write_error_requires_read_before_retry():
    tool = MagicMock()
    tool.name = "create_issue"
    result = github.handle_github_tool_error(tool, {}, None, TimeoutError("secret-value"))
    assert result["status"] == "error"
    assert "uncertain" in result["message"]
    assert "List issues" in result["message"]
    assert "secret-value" not in str(result)


def test_github_error_callback_leaves_unrelated_tool_errors_unhandled():
    tool = MagicMock()
    tool.name = "get_current_date"
    assert github.handle_github_tool_error(tool, {}, None, ValueError("other")) is None


def test_agent_registers_github_call_error_handler(monkeypatch):
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    module = importlib.import_module("agent")
    assert module.create_agent().on_tool_error_callback is github.handle_github_tool_error
