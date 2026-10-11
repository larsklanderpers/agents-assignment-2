# Implementation notes for the reflection

These are factual notes about the prepared code, not a completed personal reflection or a report of observed test results.

## Scope

Option B uses Google Tasks. Calendar is deliberately left for a later exercise. Part 2 uses the assignment's GitHub McpToolset. The optional tool-search bonus is not implemented, and no token savings are claimed.

## Tools

| Tool | Purpose |
| --- | --- |
| list_task_lists | Resolve a named list to its Google ID |
| list_tasks | Fetch outstanding or completed tasks, with explicit pagination |
| create_task | Validate and create a task with optional notes and date |
| complete_task | Patch the status to completed |
| update_task | Patch only specified fields; allow intentional clearing of notes/date |
| delete_task | Delete the task identified by its real ID |
| get_current_date | Resolve relative dates using the configured timezone |

Each Google tool returns a status dictionary and has a descriptive docstring and type hints. ADK derives function schemas from these functions.

## Design choices

- Use the supplied OAuth helper without changing it.
- Validate dates, titles, notes, IDs, and page sizes before requesting OAuth or making an API call.
- Convert dates to RFC 3339 UTC midnight. Tasks stores dates, not time-of-day reminders.
- Use patch for edits to preserve fields the user did not ask to change.
- Return page tokens instead of silently presenting a partial response as a complete list.
- Include hidden completed tasks when completed tasks are requested.
- Never echo raw exceptions, which may include local paths or request details.
- Do not automatically retry Tasks writes after an uncertain network result.
- Use both create_agent and root_agent to support the provided checks and ADK Web.
- Load .env relative to agent.py, so launching from the parent folder works.
- Keep Google Tasks usable when no GitHub token is configured.
- If GitHub discovery fails, offer a connection-status tool instead of aborting the agent. Restart ADK after fixing the connection.
- Limit GitHub MCP to repository search, issue listing/detail/creation, and file reading.
- Ask for explicit confirmation in the system instruction before writes. This is conversational behavior, not a server-side authorization boundary or a production approval mechanism.
- Correct the starter's nested credential ignore path before committing local OAuth files by mistake.

## Verification observed on 2026-10-11

Environment: Windows, Python 3.13.14, Google ADK 1.18.0, Node.js 24.14.0.

| Check | Observed result |
| --- | --- |
| Package apply script against a fresh clone | Passed; created local feat/tasks-manager |
| Offline pytest suite | 38 passed; two third-party deprecation warnings |
| Instructor Part 1 script | 8/8 checks passed |
| Instructor Part 2 script | Configuration checks passed with an explicit dummy token |
| ADK Web | HTTP 200; discovered workspace_assistant; temporary server stopped |
| Python syntax compilation and git diff --check | Passed |
| pip check | No broken requirements found |
| Credential exclusions | .env, credentials.json, and token.json all ignored |

The GitHub connection-failure regression was observed failing first, then passed after adding the fallback. The earlier tests were authored before implementation but could only be run after terminal access was restored.

The instructor scripts require Python's `-X utf8` option when their emoji/checkmark output is captured in this Windows environment. They are unchanged. The new behavior suite must be run from workspace_assistant, as shown in windows_setup.md.

Still unverified: Gemini inference, Google OAuth, actual task changes, real GitHub queries and issue creation, and conversational confirmation behavior. A dummy-token configuration check does not validate credentials. Run the live scenarios in windows_setup.md and record your actual observations in the reflection.

No remote branch, PR, merge, or submission was created in this session. The Codex GitHub connection and Windows GitHub CLI identified as larsklanderpe; the CLI had no push permission on larsklanderpers/agents-assignment-2.

## Prompts for your own reflection

- Which tool descriptions made the agent choose the correct operation?
- What actually happened during OAuth setup and the first MCP connection?
- Did the agent ask for confirmation and resolve relative dates correctly?
- What did the mocked tests prove, and what needed live testing?
- How would you extend this into the Calendar option later?

Explain your own observations in reflection_template.md and disclose AI assistance according to the course's requirements. Do not describe expected behavior as an observed successful test.
