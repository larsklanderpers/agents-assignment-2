# Assignment 2 Reflection

**Name:** Lars Klander
**Option:** B - Tasks
**Date:** October 11, 2026

*Option B: Google Tasks, GitHub MCP integration, and deferred tool-loading bonus.*

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
I chose Tasks because it provides a contained, useful workflow. Find the work, add something, change it, finish it, and remove it when appropriate. Those actions cover the life of a task without requiring the model to invent its own procedure for every request. I also figured that since it was the second choice, most of the students would do the first. After submission, I suspect I will do another fork to do the calendar too. It is an interesting project. Thanks for that. Have done a lot of stuff with AI, but believe it or not, have never written a chatbot, so that was a fun aspect too.

Anyway, as per the instructions, Calendar is outside this submission. Tasks can be displayed in Google Calendar, but the integration here creates Google Tasks, not calendar events. The bot is transparent about that, too.

### Description Strategy
The tools use action names and describe their inputs, outputs, and limitations in their docstrings. That gives ADK the information it needs to expose function schemas to the model. Listing tasks and listing task lists are separate operations; completing a task is also distinct from updating its contents. I think those distinctions make the model's choice easier to inspect. From a design perspective, actions against concepts is what I am used to, so that's how I attacked this problem.

The agent instructions require actual IDs from tool results, clarification when names are ambiguous, and confirmation before a write. Relative dates must be resolved through the date tool. Google Tasks stores a due date, not a time-of-day deadline, so the agent should explain that limitation rather than promise a reminder it cannot deliver (the dates also appear in my Google Calendar view, but the API does not provide a time-of-day deadline).

---

## Challenges Encountered

### Challenge 1: Authentication was several separate setup steps

The Gemini key, Google OAuth client, test-user access, and enabled Tasks API each serve a different purpose. Having the credentials file in place did not mean the application could read tasks. Google first blocked consent because the account needed test-user access; after authorization succeeded, the API request still failed because Google Tasks API was disabled in the project.

The fix was to add the account as a test user, complete local OAuth consent, and enable the Tasks API. A read-only API request then succeeded. That sequence made the distinction between model access and access to my Google data fairly concrete.

This is probably less of a challenge when you're used to working with the authentication model and the APIs that are at play. I haven't worked much with the Google API, and the study was really looking more at the ADK stuff. Some of this challenge in terms of getting across the initial line was purely a function of not having done a whole lot with it. For at least, I don't know, 10 or 15 minutes at one point, I kept trying to figure out why I couldn't get the client to authenticate properly. It turned out that I needed to add myself again to a different location in the application build as a test user.

### Challenge 2: Moving working code did not move a working environment

The completed code was on another computer. On the laptop, the existing repository was still the clean starter. Importing the verified Git bundle restored the finished feature branch and its history without rebuilding the implementation or replacing local work. Python, Node.js, dependencies, and local credentials still needed their own setup. This is all relatively normal stuff, but I was running into some auth conflicts between my corporate GitHub and my personal GitHub, so I just made a decision to separate the things for clarity and simplicity. It didn't really have any direct relationship to the code itself or to the Google API connection. I did end up creating a second set of keys so I could keep track of requests from here versus requests from the other as I was looking at billing and scopes.

Live testing also encountered a temporary Gemini high-demand error. As with what I experienced in week one, I chose to pin the assignment to a specific model. However, this time it was not because Google refused to acknowledge the model that I had, like it was last week. Rather, it was because when I made the change last week to the default model off of the Flash 2.5, I experienced this same error multiple times when I was testing last week. The way that I solved that last week was to move the model and pin it to Gemini 3.5 Flash because that doesn't seem to have the same level of demand. Needless to say, pinning an application to a model is not necessarily the best choice for production-level code. However, since this project has about 48 hours left in its immediate life cycle, it seemed like a de minimis problem to me. Model lifecycle management can be revisited if it becomes a longer-lived application. The pin is a practical choice for the exercise, not a guarantee against service failures.

### Challenge 3: Much of the design was an uphill effort because of the prevalence of Python.

My historic development background is in C++, C#, Java, and, more recently, React and JavaScript: business-level applications and heavy-duty coding applications, including embedded systems. I've learned enough Python to be dangerous, but not much more than that. As we continue to work with these development kits that are Python-facing, it's become obvious that I need to have a little bit more practice working with Python to make sure that I'm delivering the proper solution.

I also generally find that I have problems with design sometimes, because I find that the ease of adding features and of expanding the functionality involved in a given set (when working with AI-facing toolkits like this) means that my normal measure of where we should stop is much further out from where it would be in a development environment where I knew exactly what I was building and how long it would take. I have to be very careful not to let the infinite piece of string just continue to get longer all the time.

It's good that you said in the assignment to only do one. Otherwise, I'm pretty sure I would have done both of them, just because I wouldn't have been able to help myself in the infrastructure. That was clearly a personal issue, but it doesn't change the fact that good design requires sticking to the plan. If you're going to pick things up off to the sides of the plan, then it requires that you go back and plan those new things as well, because just throwing more stuff on top of more stuff gives you a giant blob of junk.


---

## Error Handling Approach

Anyway, back to this project. Even though it's a reflection, pretty sure it's not meant to be a philosophical statement. The tool layer validates titles, IDs, notes, dates, and page sizes before making an API request. It returns structured success or error results, with messages for missing credentials, expired authorization, denied access, missing tasks, rate limits, and service failures. Raw exceptions are kept out of the tool response because they can contain details the user does not need, including credentials or request information.

An uncertain write is particularly important. If a request times out, the task may already exist; automatically trying again can create a duplicate. The agent is instructed to check the current state before retrying and to report success only after a successful tool result. Confirmation is currently enforced through the agent instructions. It is not a separate application-level approval gate, and I would strengthen that before relying on this in production.

### Verification to first breakpoint

At the first breakpoint on the laptop, 38 offline tests passed, the instructor's Part 1 checks passed 8/8, and dependency checks passed. ADK Web started and discovered the agent. A live Gemini request called the date tool and returned the correct date in the configured Los Angeles timezone. A direct Google Tasks API read succeeded after setup was corrected.

I also created three sample tasks during live testing and checked that they appeared in my Google Calendar view. That is my observed creation result. It does not establish that updating, completing, deleting, pagination, or every confirmation scenario has passed live testing. I then performed all the tasks identified in the assignment against the task list using the task API and the agent that had been created to interpret them. That went relatively smoothly. There was nothing in particular that was problematic with that process. There were some issues where connectivity was a bit sketchy, but that was nothing to do with the app itself. That was just something to do with Gemini.

### Verification to second breakpoint

Once we confirmed that the task API was working properly, I went ahead and added the MCP surface for GitHub. This came with its own set of issues, mostly having to do with authentication not working the way I thought it was going to. Ultimately, I was able to list repositories, list issues inside of a repository, and add a fresh issue to a repository. All that functionality, as requested in the assignment, was working properly through the chat interface. It was updating the detail correctly.

The biggest thing here, which is just sort of a constant of development in my experience, was that just because it worked once doesn't mean it's going to work the same way on the second thing. The GitHub MCP had a different set of considerations that had to be met and didn't read from where I put my PAT key, and it just wasn't playing nicely.

Moreover, as we don't use issues in our business much at present, I wasn't really focused on checking the box, as it were, for issues when I created the base repo (which was a fork off of your repo). Issue creation kept failing because Issues were disabled on the repository. This was a repository setting, rather than an authentication failure. Enabling Issues addressed that problem, and the agent then created the test issue successfully. It's probably worthwhile to have a bot or something watching each of these things as they're created. As we continue to establish standards for how you expect to get them, the bot actually makes sure that:

- the code and the structure are in line with that
- the PAT is tested against the GitHub MCP
- Google OAuth is confirmed

The agent should explain what needs to happen next. In the event that an MCP does not return a result because there is a permissions or other error, the error message should come back with some kind of meaningful indication, not just error 500: some kind of meaningful indication about the fact that there was an error and the error had to do with this. This is what you should go fix and then try again, which is pretty straightforward but also not necessarily super common.

### Verification to third breakpoint

For the bonus, I implemented tool search so the model does not need every GitHub tool description in every request. There was a wrinkle here: the instructions called for `McpToolset(defer_loading=True)`, but that argument is not available on the base toolset in the installed ADK 1.18. Checking the constructor confirmed that it was not supported in that version.

So, I subclassed `McpToolset` as `GitHubMcpToolset`, added the argument there, and used `get_tools(context)` to control which tool schemas ADK sends to the model. The MCP connection still discovers the catalog locally. What is deferred is exposing those descriptions and input definitions to the model. `create_agent_with_tool_search()` builds this version, and it is the default agent used by the interface.

Initially, the GitHub tools available to the model are repository search and `search_github_tools`. If I ask for open issues, the model first searches for the capability to list issues. That search matches keywords against the allowed tools' names and descriptions, records up to two best matches in the current session, and makes their schemas available on the next model step. The model can then call `list_issues` through the real MCP connection. A new search replaces the previous selection, so the list does not just keep growing, and one session's choices do not affect another. Finding a tool does not execute it or authorize a write; the confirmation rules still apply. I verified the search-to-tool sequence with both an offline ADK runner test and a live Gemini request. In the context comparison, the full 26-tool catalog used 5,593 prompt tokens and the deferred version used 2,176, a saving of 3,417 tokens, or 61.09%. Against the five-tool allowlist already used in this project, the saving was smaller: 2,451 down to 2,176, or 11.22%. Those are whole-prompt counts, including the task tools and instructions. Search also adds a model step when a capability needs to be loaded, so the smaller initial context does not guarantee a cheaper conversation in every case.

Token savings were substantial as a function of the pattern implementation:

| Configuration | Prompt tokens | Tokens saved by deferral | Reduction |
|---|---:|---:|---:|
| Before: full 26-tool catalog | 5,593 | 3,417 | 61.09% |
| Before: five-tool allowlist | 2,451 | 275 | 11.22% |
| After: deferred loading | 2,176 | Reference | Reference |

While the 61% did not quite get to the approximate 80% in the assignment example, this measures the whole prompt, including the task tools and system instructions. The original implementation already limited GitHub to five tools; the deferred version starts with two. I also ran the full 26-tool catalog as a separate comparison, which produced the 5,593-token baseline above. Against the existing five-tool implementation, the saving was 11.22%. There is still room to experiment, but I did not remove confirmation or error-handling instructions just to make the number look better. The final offline suite passed 55 tests.

---

## Ideas for Improvement

If you had more time, what would you add or change?

1. Add an application-level approval gate for mutations so confirmation does not depend solely on the model following instructions.
2. I also think I'd probably make it a bit more willing to do things without independent confirmation being requested again. If the phrasing of the request is such that it has a great deal of confidence, then it should perform the task without coming back and confirming. For everything else, a delete task should always be confirmed.
3. Add repeatable live conversation checks for ambiguous task names, relative dates, rejected changes, and uncertain write results.
4. I'd also like to get a bit more into it with all these different APIs that Google has. I think it would be interesting to take a list of tasks like we've generated here and email them to somebody (be it myself or somebody else) through the Gmail API. I think it'd be really interesting to set a follow-up from the calendar utility to a task that was 24 hours after the task was due, to make sure there was some sort of review process happening and post-implementation evaluation with the team.
5. After submission, fork the repository and add Calendar support, with a clear distinction between a task due date and a scheduled event.
6. On the bonus assignment, I would probably implement the delayed load pattern for the task tools as well, so that the tasks were only loaded when needed, instead of all in advance. That would have to be closely interrogated for performance implications and responsiveness, but implementing the pattern itself feels like it would be straightforward.
7. I think adding a date range to the task listing tool would be pretty useful. Pagination is already implemented, but a date filter would narrow the results before they reach the model. With enough tasks, that could make requests more focused and reduce the amount of task data included in the conversation.
8. Ultimately it feels like the GitHub deferred load would benefit by some local persistence of usage information -- i.e., these five tools have been used in the last 24 hours, load them separate from the deferred-loading and first, and then you are balancing usage with tokens. Not sure, but I can't help but feel like there is some more optimization across a wider access pattern to be had there.

---

## Key Learnings

What did you learn from this assignment about building AI agents?

I think the useful lesson here is how many things have to agree before a small agent can do something real. The model needs understandable tools; the tools need valid inputs; Google needs the correct credentials, consent, and enabled API; and the result needs to show up where I can check it. The code was already implemented when the laptop setup began, but there was still work between having that code and seeing three real tasks in my account.

The testing also made me more careful about what a passing result actually proves. An offline test can show that a function handles a mocked response correctly. It cannot show that my Google project is configured correctly or that a live conversation waits for approval. Seeing a task appear provides stronger evidence for creation, but it says nothing by itself about deletion. Each claim needs its own evidence.

Finally, it is clear that optimizing for cost has different implications than optimizing for speed. The GitHub pattern reduces the initial context, but finding a deferred tool adds a model step, so a speed improvement is not guaranteed. Deferring the task tool schemas might simply move some of the cost to a later step, since a task-focused conversation is likely to need them anyway. That would need measurement rather than assumption.
