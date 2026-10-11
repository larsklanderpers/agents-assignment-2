# Run the Tasks Manager on Windows

This implements Option B and the required GitHub MCP integration. Use a local checkout in VS Code. ADK provides the chat interface in your browser.

## 1. Install the local dependencies

Use Python 3.11 or newer, Git, and Node.js LTS. This Windows machine already has Python 3.13, so no second Python installation is needed. Open a new terminal after installing any missing prerequisite. These instructions use PowerShell 7 and avoid changing execution policy or activating a virtual environment.

From the repository root, the folder containing `workspace_assistant`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\workspace_assistant\requirements-task-manager.txt
node --version
npx.cmd --version
```

Stop if dependency installation fails. The extra requirements file pins Google ADK to 1.18.0 and leaves the instructor's requirements file untouched. It also installs timezone data for Windows. This build passed 38 offline tests on Windows with Python 3.13.14. Live Google and GitHub transactions still require your credentials and testing.

## 2. Configure Gemini

Create an API key at [Google AI Studio](https://aistudio.google.com/apikey).

Copy the example only if `.env` does not already exist:

```powershell
if (-not (Test-Path -LiteralPath .\workspace_assistant\.env)) {
    Copy-Item -LiteralPath .\workspace_assistant\.env.example -Destination .\workspace_assistant\.env
}
code .\workspace_assistant\.env
```

Edit the local file:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_real_key_here
MODEL_NAME=gemini-flash-latest
TIMEZONE=Australia/Sydney
GITHUB_PERSONAL_ACCESS_TOKEN=
GITHUB_USERNAME=larsklanderpers
```

Leave GitHub blank for the first Google Tasks test. The agent will say GitHub is not configured while Tasks remains available. If you use another timezone, replace Australia/Sydney with its IANA name.

The Gemini key powers the model. It does not grant access to your Google Tasks. [Gemini key documentation](https://ai.google.dev/gemini-api/docs/api-key)

## 3. Configure Google Tasks OAuth

1. In [Google Cloud Console](https://console.cloud.google.com/), create or select your project.
2. Enable **Google Tasks API** in the API Library.
3. Configure **Google Auth Platform > Branding** with an app name and your email.
4. For a personal Google account, select **External** under Audience, keep the app in testing, and add your email as a test user.
5. Under Data Access, add `https://www.googleapis.com/auth/tasks` if configuring scopes. The supplied OAuth helper requests this read/write scope.
6. Under **Clients**, create a **Desktop app** client. Download its JSON.
7. Save it as `workspace_assistant/config/credentials/credentials.json` in the repository. Create the directory if needed. The name must be exactly `credentials.json`, not `credentials.json.json`.

Use the same Google account whose tasks you want to manage when the browser asks for consent. The first Tasks call opens the OAuth browser flow and saves `token.json` automatically. Do not create token.json yourself.

To authorize before starting chat, run from the repository root:

```powershell
Set-Location .\workspace_assistant
..\.venv\Scripts\python.exe -c "from tools.auth import get_tasks_service; get_tasks_service(); print('Google Tasks authorization succeeded')"
Set-Location ..
```

This only initializes the authorized client; it does not create or delete tasks. [Google Tasks setup guide](https://developers.google.com/workspace/tasks/quickstart/python)

The provided OAuth helper uses that fixed credentials location. Changing `GOOGLE_CREDENTIALS_PATH` alone does not relocate its files.

## 4. Run the offline checks

From the repository root:

```powershell
Set-Location .\workspace_assistant
..\.venv\Scripts\python.exe -m pytest -q tests/test_task_manager.py
..\.venv\Scripts\python.exe -X utf8 -m tests.test_tools
Set-Location ..
```

Expected: pytest passes and the instructor's Tasks and agent checks report 8/8. The new tests mock Google APIs and do not make Gemini requests or launch a GitHub server. The provided check script prints a summary rather than failing the process reliably, so read its output. The UTF-8 flag allows its checkmarks and emoji to print correctly on Windows without editing the supplied tests.

Record actual results in the reflection. Do not record these expected results as observed until you run them.

## 5. Start ADK Web

Run from the repository root, one level above `workspace_assistant`:

```powershell
.\.venv\Scripts\adk.exe web --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> and choose `workspace_assistant`. Keep the terminal running. Use Ctrl+C to stop it. After editing `.env`, stop and restart ADK.

The package adds `root_agent` and supports both direct imports used by the instructor's tests and package imports used by ADK Web. The correct launch directory follows [Google's ADK quickstart](https://adk.dev/get-started/python/).

For a terminal conversation, the supported alternative is:

```powershell
.\.venv\Scripts\adk.exe run workspace_assistant
```

Use ADK Web or `adk run` for testing this implementation. The instructor's `main.py` is left unchanged; it constructs a runner without explicitly creating a session, so it is not the recommended launch path for this package.

Try these in order:

1. `Show my task lists, then show my outstanding tasks.`
2. `Add a task called Assignment 2 smoke test, due tomorrow.` Confirm the displayed date and creation.
3. `Change the notes on Assignment 2 smoke test to Tested through ADK Web.` Confirm.
4. `Mark Assignment 2 smoke test complete.` Confirm.
5. `Show completed tasks.` Check that the test task appears.
6. `Delete Assignment 2 smoke test.` Confirm only that test task.

Check the task in Google Tasks as well as the chat response. Test an invalid date and an ambiguous task name. The agent should clarify or explain the error rather than invent an ID or claim success.

## 6. Enable GitHub MCP

The assignment explicitly uses the npm server `@modelcontextprotocol/server-github` and a classic personal access token with `repo` scope. That scope grants broad repository access. Use a short expiry for the class exercise and keep the token only in `.env`. The server is the assignment's legacy reference implementation; the bonus deferred-loading pattern is not implemented or claimed here.

1. Open GitHub **Settings > Developer settings > Personal access tokens > Tokens (classic)**.
2. Generate a classic token with an expiry and the scope specified by the assignment, `repo`.
3. Put the token in your local `GITHUB_PERSONAL_ACCESS_TOKEN` setting.
4. Set `GITHUB_USERNAME` to the username whose repositories you want to list.
5. Restart ADK.

[GitHub's token documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

Run the instructor's Part 2 check:

```powershell
Set-Location .\workspace_assistant
..\.venv\Scripts\python.exe -X utf8 -m tests.test_mcp
Set-Location ..
```

This checks local prerequisites and McpToolset presence, not a complete live GitHub transaction. In ADK Web, test:

1. `List my GitHub repositories.`
2. `Show open issues in larsklanderpers/agents-assignment-2.`
3. `Create an issue in larsklanderpers/agents-assignment-2 titled Assignment 2 MCP test, with body: Temporary issue to verify the class integration.` Confirm the exact repository and text.

Creating the test issue is a real GitHub write. Check its returned URL, then close the test issue in GitHub when finished. Repository search lists repositories owned by the configured username; it is not an inventory of every organization repository accessible to the token.

The first request may take longer while npx downloads the server. Windows uses `npx.cmd`; other platforms use `npx`. Only five relevant GitHub tools are exposed to the agent.

## Troubleshooting

- **Model authentication fails:** check `GOOGLE_API_KEY`, that it belongs to your intended Google project, and that Vertex AI mode is false. Restart ADK.
- **Model not found or quota exhausted:** choose an available model shown for your key in AI Studio, or resolve that project's quota, then update MODEL_NAME and restart. Model availability and quota depend on the account.
- **OAuth access blocked:** check the test-user email and sign in with the account added there. Use a Desktop client, not a Web application client.
- **Expired or revoked OAuth token:** stop ADK, move `token.json` out of `config/credentials` to a private location, then rerun the authorization command. This causes a fresh consent flow. Keep credentials.json in place.
- **Tasks permission denied:** ensure the API is enabled and the OAuth grant includes the Tasks read/write scope. A quota limit can also return 403.
- **GitHub fails during startup:** the agent offers a connection-status tool and keeps Google Tasks available. Check Node and npx, token expiry, and repository permissions, then restart ADK to retry the connection. You can also temporarily clear only the GitHub value in your local `.env` and restart to test Google Tasks separately.
- **No agent in the dropdown:** launch from the repository root and check that `workspace_assistant/__init__.py` and `root_agent` are present.
- **Times disappear from tasks:** the Tasks API stores the calendar date, not a time-of-day reminder. This is an API limitation, not a Calendar integration. [Tasks resource reference](https://developers.google.com/workspace/tasks/reference/rest/v1/tasks)

## 7. Prepare the submission

Complete `docs/reflection_template.md` with your actual observations. `docs/implementation_notes.md` supplies factual design notes to help you explain the implementation. Record offline and live test results separately.

From the repository root, check the branch and credential exclusions before committing:

```powershell
git branch --show-current
git check-ignore workspace_assistant/.env workspace_assistant/config/credentials/credentials.json workspace_assistant/config/credentials/token.json
git status --short
git diff --check
```

The branch should be `feat/tasks-manager`; check-ignore should print all three credential paths. Review the diff, then explicitly stage the build's files:

```powershell
git add .gitignore session_notes.md workspace_assistant/agent.py workspace_assistant/__init__.py workspace_assistant/.env.example workspace_assistant/requirements-task-manager.txt workspace_assistant/tools/tasks_tools.py workspace_assistant/tools/mcp_tools.py workspace_assistant/tests/test_task_manager.py workspace_assistant/docs/windows_setup.md workspace_assistant/docs/implementation_notes.md workspace_assistant/docs/reflection_template.md
git diff --cached --stat
git commit -m "feat(tasks): implement assignment task manager and GitHub MCP"
git push -u origin feat/tasks-manager
```

Update session_notes.md with actual test results in the same commit. Open a pull request into main and review it. Per Lars's global instructions, merging requires his explicit go; the apply script neither commits nor merges.

The assignment is graded from **main**, so a feature branch alone is not a completed submission. After the approved merge, verify the files on GitHub. Also verify that this personal fork is the repository expected by the class or submit its link through the class's required channel. The provided grader workflow depends on instructor configuration; it is not proof of submission merely because it exists.
