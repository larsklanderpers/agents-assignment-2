"""Live, read-only bonus comparison. Run: python -m tests.compare_tool_context.

Requires configured Gemini and GitHub credentials. Prints counts and tool names,
never credentials, repository contents, or issue bodies. No writes are allowed.
"""

import asyncio
import json

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.genai import types

from agent import create_agent, create_agent_with_tool_search


async def run_case(mode: str, *, verify_search: bool = False) -> dict:
    deferred = mode == "deferred"
    agent = create_agent_with_tool_search() if deferred else create_agent()
    toolset = next(tool for tool in agent.tools if isinstance(tool, McpToolset))
    if mode == "full_catalog":
        # Comparison only: production keeps its five-capability allowlist.
        toolset.tool_filter = None
    requests, calls = [], []

    def capture(callback_context, llm_request):
        declarations = [declaration for tool in llm_request.config.tools or []
                        for declaration in tool.function_declarations or []]
        github = [declaration for declaration in declarations
                  if declaration.name not in {
                      "list_task_lists", "list_tasks", "create_task", "complete_task",
                      "update_task", "delete_task", "get_current_date"}]
        requests.append({
            "github_schemas": [declaration.name for declaration in github],
            "github_schema_characters": len(json.dumps(
                [declaration.model_dump(mode="json", exclude_none=True)
                 for declaration in github], separators=(",", ":"))),
        })

    def prevent_writes(tool, args, tool_context):
        allowed = {"search_github_tools", "search_repositories", "list_issues", "get_issue"}
        if not verify_search or tool.name not in allowed:
            raise RuntimeError("Comparison forbids this tool call: " + tool.name)
        calls.append(tool.name)

    agent.before_model_callback = capture
    agent.before_tool_callback = prevent_writes
    sessions = InMemorySessionService()
    await sessions.create_session(app_name="context_comparison", user_id="test", session_id="fresh")
    runner = Runner(agent=agent, app_name="context_comparison", session_service=sessions)
    prompt = ("Show the open issues in larsklanderpers/agents-assignment-2. Read only."
              if verify_search else "Do not call any tools. Reply with just Ready.")
    try:
        events = [event async for event in runner.run_async(
            user_id="test", session_id="fresh",
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            run_config=RunConfig(max_llm_calls=8))]
        errors = [event.error_code for event in events if event.error_code]
        if errors:
            raise RuntimeError("Model error: " + str(errors))
        tokens = [event.usage_metadata.prompt_token_count for event in events
                  if event.usage_metadata and event.usage_metadata.prompt_token_count]
        if not tokens:
            raise RuntimeError("No prompt token usage returned by Gemini")
        if verify_search:
            assert calls[0] == "search_github_tools", calls
            assert "list_issues" in calls, calls
            responses = [response for event in events for response in event.get_function_responses()
                         if response.name == "list_issues"]
            assert responses, "No issue read response"
            response = responses[-1].response
            assert not response.get("isError") and response.get("status") != "error", "Issue read failed"
            assert response.get("content"), "No MCP response content"
            assert "list_issues" not in requests[0]["github_schemas"]
            assert any("list_issues" in request["github_schemas"] for request in requests[1:])
        return {"mode": mode, "prompt_tokens": tokens, "requests": requests, "calls": calls}
    finally:
        await toolset.close()


async def main():
    results = []
    for mode in ("full_catalog", "allowlist", "deferred"):
        result = await run_case(mode)
        results.append(result)
        print(json.dumps(result), flush=True)
    baseline, allowlist, deferred = [result["prompt_tokens"][0] for result in results]
    print(json.dumps({
        "full_prompt_reduction_percent": round(100 * (baseline - deferred) / baseline, 2),
        "allowlist_prompt_reduction_percent": round(100 * (allowlist - deferred) / allowlist, 2),
        "note": "Prompt tokens include system instructions, task tools, GitHub tools, and the same user prompt. Schema characters are a separate size measure, not tokens.",
    }), flush=True)
    print(json.dumps(await run_case("deferred", verify_search=True)), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
