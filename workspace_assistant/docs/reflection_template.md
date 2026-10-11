# Assignment 2 Reflection

**Name:** Lars Klander
**Option:** B - Tasks
**Date:** October 11, 2026

*Required Tasks, GitHub MCP, and the optional tool-search bonus were live-tested.*

---

## Tool Design Decisions

### Tools Implemented
1. **list_task_lists**: Find available task lists and their real IDs.
2. **list_tasks**: Retrieve outstanding tasks, or completed tasks when requested.
3. **create_task**: Create a task with a title, optional notes, and a due date.
4. **complete_task**: Mark an existing task complete.
5. **update_task**: Change specified fields while preserving everything else.
6. **delete_task**: Delete the selected task by its ID.

The agent also has **get_current_date**, which supplies the local date and timezone before it interprets a request such as "tomorrow."

### Why These Tools?
I chose Tasks because it provides a contained, useful workflow. Find the work, add something, change it, finish it, and remove it when appropriate. Those actions cover the life of a task without requiring the model to invent its own procedure for every request.

Calendar is outside this submission. Tasks can be displayed in Google Calendar, but the integration here creates Google Tasks, not calendar events. After submission, I plan to fork the repository and add Calendar separately. For this assignment, I wanted the scope to stay where I put it.

### Description Strategy
The tools use action names and describe their inputs, outputs, and limitations in their docstrings. That gives ADK the information it needs to expose function schemas to the model. Listing tasks and listing task lists are separate operations; completing a task is also distinct from updating its contents. I think those distinctions make the model's choice easier to inspect.

The agent instructions require actual IDs from tool results, clarification when names are ambiguous, and confirmation before a write. Relative dates must be resolved through the date tool. Google Tasks stores a due date, not a time-of-day deadline, so the agent should explain that limitation rather than promise a reminder it cannot deliver.

---

## Challenges Encountered

### Challenge 1: Authentication was several separate setup steps

The Gemini key, Google OAuth client, test-user access, and enabled Tasks API each serve a different purpose. Having the credentials file in place did not mean the application could read tasks. Google first blocked consent because the account needed test-user access; after authorization succeeded, the API request still failed because Google Tasks API was disabled in the project.

The fix was to add the account as a test user, complete local OAuth consent, and enable the Tasks API. A read-only API request then succeeded. That sequence made the distinction between model access and access to my Google data fairly concrete.

### Challenge 2: Moving working code did not move a working environment

The completed code was on another computer. On the laptop, the existing repository was still the clean starter. Importing the verified Git bundle restored the finished feature branch and its history without rebuilding the implementation or replacing local work. Python, Node.js, dependencies, and local credentials still needed their own setup.

Live testing also encountered a temporary Gemini high-demand error. I chose to pin the assignment to `gemini-3.5-flash`, after checking that it was available to my key. This project has about 48 hours left in its immediate life cycle; model lifecycle management can be revisited if it becomes a longer-lived application. The pin is a practical choice for the exercise, not a guarantee against service failures.

---

## Error Handling Approach

The tool layer validates titles, IDs, notes, dates, and page sizes before making an API request. It returns structured success or error results, with messages for missing credentials, expired authorization, denied access, missing tasks, rate limits, and service failures. Raw exceptions are kept out of the tool response because they can contain details the user does not need, including credentials or request information.

An uncertain write is particularly important. If a request times out, the task may already exist; automatically trying again can create a duplicate. The agent is instructed to check the current state before retrying and to report success only after a successful tool result. Confirmation is currently enforced through the agent instructions. It is not a separate application-level approval gate, and I would strengthen that before relying on this in production.

### Verification so far

On the laptop, 53 offline tests passed, the instructor's Part 1 checks passed 8/8, and dependency checks passed. ADK Web started and discovered the agent. A live Gemini request called the date tool and returned the correct date in the configured Los Angeles timezone. A direct Google Tasks API read succeeded after setup was corrected.

I also created three sample tasks during live testing and checked that they appeared in my Google Calendar view. In a later visible ADK Web test, the agent listed those tasks, proposed a disposable task due tomorrow, and waited for confirmation before creating it. The Google API confirmed its notes, date, and pending status. A proposed notes update was canceled; both the API state and tool-call history confirmed that no update occurred. After a fresh proposal and confirmation, the notes changed while the title and date stayed intact. Completion also waited for confirmation, and the completed task appeared in a subsequent listing.

A separate live pagination check returned different tasks on consecutive pages. Tool-level checks rejected an impossible date and an empty title before API access. In my own visible conversation, I created and completed a garbage task, created a dated throwaway task called "Friday Happy Hour Visit Disposable," updated the notes of a class-preparation task after clarifying which item I meant, and confirmed deletion of the throwaway task. The session records show a successful `delete_task` response. That completes the basic live task lifecycle; it does not mean every possible ambiguity or service failure has been tested.

For GitHub MCP, live repository searches and issue reads returned results. Issue creation initially failed because Issues were disabled on the target repository. A direct GitHub API check confirmed that setting. After it was enabled, the agent successfully created issue #2 in `larsklanderpers/agents-assignment-2`, titled "Change primary language from Python to COBOL." That deliberately implausible change request was test data, not a plan to rewrite this project. The session records contain the successful MCP response and the issue URL.

The initial MCP invocation error also exposed a code defect: the discovery-only error handler did not catch a rejected tool call, so the agent could not explain the actual failure. A call-error callback now maps that rejection to an actionable message; four added regression checks pass. That specific failure path still needs a live retest after the server reloads the fix. The successful issue creation verifies the required write workflow, while the regression tests cover the corrected error handling.

### Bonus: Tool search and context comparison

I kept repository search always available and added `search_github_tools` to find the other supported capabilities. `create_agent_with_tool_search()` configures `GitHubMcpToolset` with `defer_loading=True`. The installed ADK 1.18 does not accept that argument on its base `McpToolset`, so the subclass implements schema selection through `get_tools(context)`. It still uses the real MCP connection and tools. The server catalog is discovered locally, while the model initially receives only repository search and tool search.

Search loads up to two best matches for the next model step. A new search replaces the previous selection, and that selection belongs to the session. Loading a tool does not execute it or approve a write. The original confirmation instructions remain in place.

I ran fresh agents with the same short request: "Do not call any tools. Reply with just Ready." The full-catalog comparison temporarily removed the allowlist; it was a measurement run, not the production configuration. These are Gemini's returned prompt-token counts, including the task tools, system instructions, GitHub schemas, and user message:

| Configuration | GitHub schemas initially loaded | Prompt tokens |
|---|---:|---:|
| Without deferral, full server catalog | 26 | 5,593 |
| Without deferral, existing capability allowlist | 5 | 2,451 |
| With deferral | 2: repository search and tool search | 2,176 |

The reduction against the full catalog is `(5,593 - 2,176) / 5,593 × 100 = 61.09%`. Against the existing five-tool allowlist, it is **11.22%**. The assignment's approximate 80% example is not what this whole-prompt measurement produced. Serialized GitHub schema size fell from 13,654 to 866 characters, or **93.66%**, but characters are not tokens. Fixed task tools and instructions remain in every prompt, and the deferred agent also needs instructions explaining search.

A separate live read asked for open issues. Gemini first called `search_github_tools`, then used the newly loaded `list_issues` tool successfully. An offline ADK runner test verifies that same transition with a scripted model. Other tests cover session isolation, replacing selections, missing matches, invalid searches, and connection failure. The reproducible read-only comparison is `python -m tests.compare_tool_context` from `workspace_assistant`.

There is a tradeoff: discovery adds a model step, and conversation history grows after each tool result. A smaller initial prompt does not guarantee lower total tokens or lower latency for every conversation. I would measure the actual workload before treating deferral as a universal improvement.

---

## Ideas for Improvement

If you had more time, what would you add or change?

1. Add an application-level approval gate for mutations so confirmation does not depend solely on the model following instructions.
2. Add repeatable live conversation checks for ambiguous task names, relative dates, rejected changes, and uncertain write results.
3. After submission, fork the repository and add Calendar support, with a clear distinction between a task due date and a scheduled event.

---

## Key Learnings

What did you learn from this assignment about building AI agents?

I think the useful lesson here is how many things have to agree before a small agent can do something real. The model needs understandable tools; the tools need valid inputs; Google needs the correct credentials, consent, and enabled API; and the result needs to show up where I can check it. The code was already implemented when the laptop setup began, but there was still work between having that code and seeing three real tasks in my account.

The testing also made me more careful about what a passing result actually proves. An offline test can show that a function handles a mocked response correctly. It cannot show that my Google project is configured correctly or that a live conversation waits for approval. Seeing a task appear provides stronger evidence for creation, but it says nothing by itself about deletion. Each claim needs its own evidence.

I selected the Tasks scope and checked the sample tasks myself. My next review is to make sure the written explanation matches both the code and what I actually observed, then verify the final repository contents before submission.
