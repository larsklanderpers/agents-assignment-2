# Assignment 2 session notes

**CURRENT BRANCH:** feat/tasks-manager (local). No remote branch was created by Codex.

**OPEN PRs:** None created in this session.

**EXTERNAL DEPENDENCIES:** Gemini API key; Google Tasks Desktop OAuth; GitHub PAT; personal-account GitHub write access. Local verification used Python 3.13.14, Node.js 24.14.0, and Google ADK 1.18.0.

## 2026-10-11: Tasks Manager implementation prepared

Lars approved Option B, the required GitHub MCP integration, and feat/tasks-manager, with no Jira ticket. The instructor's auth helper, settings, main.py, and verification tests are unchanged. Calendar and the bonus tool-search pattern remain out of scope.

Prepared six Tasks tools, a current-date tool, ADK agent/root_agent, GitHub MCP configuration, mocked behavior tests, corrected credential exclusions, and Windows setup instructions. The original reflection template still needs Lars's personal observations.

The package was initially written under outputs because sandboxed terminal startup failed and GitHub branch creation returned HTTP 403, Resource not accessible by integration. Terminal access was restored through the approved unsandboxed execution route. The package was applied to a fresh scratch clone and verified before saving the finished repository under outputs/agents-assignment-2.

Observed verification: 38 offline tests passed; instructor Part 1 checks passed 8/8; instructor Part 2 configuration checks passed with a dummy token; ADK Web returned HTTP 200 and discovered workspace_assistant; pip check found no broken requirements. The temporary Web server was stopped. UTF-8 mode is needed for the instructor scripts' printed symbols on Windows; the scripts remain unchanged.

The GitHub connection-failure test was observed failing first, then passed after implementation. Earlier tests were authored first but first executed after implementation because the terminal was unavailable. No live Google or GitHub changes were made.

Both the Codex GitHub connector and Windows GitHub CLI last identified as larsklanderpe. The CLI reported push=false on the personal repository. Signing into github.com in Chrome does not by itself establish new credentials for these existing connections.

Next: configure local credentials, run live checks, complete the reflection, update this note with results, push feat/tasks-manager using the personal GitHub account, and obtain Lars's approval before merging into main for submission. Confirm the repository matches the class submission process. No merge is authorized by the implementation go-ahead.
