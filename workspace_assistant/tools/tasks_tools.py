"""Google Tasks tools for Option B, using the supplied OAuth helper."""

from datetime import date
import re
from typing import Optional

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from .auth import get_tasks_service


class _InputError(ValueError):
    """A validation message safe to show to the user."""


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _InputError(f"Provide a non-empty {label}. List tasks or task lists to find its ID.")
    return value.strip()


def _title(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 1024:
        raise _InputError("The task title must contain between 1 and 1024 characters.")
    return value.strip()


def _notes(value: str) -> str:
    if not isinstance(value, str) or len(value) > 8192:
        raise _InputError("Task notes must be text of at most 8192 characters.")
    return value


def _due_timestamp(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise _InputError("Use a due date in YYYY-MM-DD format. Google Tasks stores dates, not times.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise _InputError("That date does not exist. Use a valid calendar date in YYYY-MM-DD format.") from None
    # Tasks discards the time portion; UTC midnight preserves the requested calendar date.
    return f"{parsed.isoformat()}T00:00:00.000Z"


def _page_size(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 100:
        raise _InputError("max_results must be an integer between 1 and 100.")
    return value


def _task_summary(task: dict) -> dict:
    return {key: task[key] for key in ("id", "title", "notes", "status", "due", "completed") if key in task}


def _error_result(error: Exception) -> dict:
    if isinstance(error, _InputError):
        return {"status": "error", "code": "invalid_input", "message": str(error)}
    if isinstance(error, FileNotFoundError):
        code = "missing_credentials"
        message = "Save your Google Desktop OAuth JSON as workspace_assistant/config/credentials/credentials.json, then try again."
    elif isinstance(error, RefreshError):
        code = "authentication_error"
        message = "Google authorization has expired or was revoked. Reauthorize using the steps in docs/windows_setup.md."
    elif isinstance(error, HttpError):
        status = error.resp.status
        messages = {
            400: ("invalid_request", "Google rejected the request. Check the task details and date format."),
            401: ("authentication_error", "Google authorization failed. Reauthorize using docs/windows_setup.md."),
            403: ("permission_denied", "Google denied access. Check that the Tasks API is enabled, your account is a test user, and Tasks access was granted. This may also be a quota limit."),
            404: ("not_found", "That task or task list was not found. Refresh the list and choose its current ID."),
            429: ("rate_limited", "Google Tasks is rate limiting requests. Wait briefly before trying again."),
        }
        if status >= 500:
            code, message = "service_unavailable", "Google Tasks is temporarily unavailable. Check your tasks before retrying a change, because it may already have reached Google."
        else:
            code, message = messages.get(status, ("api_error", "Google Tasks could not finish the request. Refresh the list and check your access."))
    elif isinstance(error, (TimeoutError, ConnectionError, OSError)):
        code = "network_error"
        message = "Could not reach Google Tasks. Check your connection and your task list before retrying a change, because it may already have reached Google."
    else:
        code = "unexpected_error"
        message = "Could not finish the Google Tasks request. Check your setup and task list before retrying a change."
    # Exceptions can contain tokens, request URLs, and local paths.
    return {"status": "error", "code": code, "message": message}


def list_task_lists(max_results: int = 100, page_token: str = "") -> dict:
    """List Google task lists and their IDs so a named list can be selected.

    Args:
        max_results: Maximum lists on this page, from 1 to 100.
        page_token: next_page_token from a previous result, or empty for the first page.

    Returns:
        A status, task_lists with id and title, and next_page_token; or a friendly error.
    """
    try:
        limit = _page_size(max_results)
        service = get_tasks_service()
        result = service.tasklists().list(maxResults=limit, pageToken=page_token or None).execute()
        lists = [{"id": item["id"], "title": item.get("title", "")} for item in result.get("items", [])]
        return {"status": "success", "task_lists": lists, "next_page_token": result.get("nextPageToken", "")}
    except Exception as error:
        return _error_result(error)


def list_tasks(task_list_id: str = "@default", show_completed: bool = False,
               max_results: int = 100, page_token: str = "") -> dict:
    """List outstanding tasks, or include completed tasks, from a Google task list.

    Args:
        task_list_id: ID from list_task_lists; @default selects the default list.
        show_completed: Include completed and hidden completed tasks when true.
        max_results: Maximum tasks on this page, from 1 to 100.
        page_token: next_page_token from a previous result, or empty for the first page.

    Returns:
        A status, tasks containing their IDs and details, and next_page_token; or an error.
    """
    try:
        list_id = _identifier(task_list_id, "task list ID")
        limit = _page_size(max_results)
        if not isinstance(show_completed, bool):
            raise _InputError("show_completed must be true or false.")
        service = get_tasks_service()
        result = service.tasks().list(
            tasklist=list_id, showCompleted=show_completed, showHidden=show_completed,
            showDeleted=False, maxResults=limit, pageToken=page_token or None,
        ).execute()
        return {"status": "success", "tasks": [_task_summary(task) for task in result.get("items", [])],
                "next_page_token": result.get("nextPageToken", "")}
    except Exception as error:
        return _error_result(error)


def create_task(title: str, notes: str = "", due_date: str = "", task_list_id: str = "@default") -> dict:
    """Create a Google task after the user confirms its title, list, and optional date.

    Args:
        title: Non-empty task title, at most 1024 characters.
        notes: Optional description, at most 8192 characters.
        due_date: Optional YYYY-MM-DD date. Times and reminders are not supported by this API.
        task_list_id: ID from list_task_lists, or @default for the default list.

    Returns:
        A status and the created task including its real ID, or a friendly error.
    """
    try:
        list_id = _identifier(task_list_id, "task list ID")
        body = {"title": _title(title), "notes": _notes(notes)}
        if due_date:
            body["due"] = _due_timestamp(due_date)
        service = get_tasks_service()
        task = service.tasks().insert(tasklist=list_id, body=body).execute()
        return {"status": "success", "task": _task_summary(task)}
    except Exception as error:
        return _error_result(error)


def complete_task(task_id: str, task_list_id: str = "@default") -> dict:
    """Mark an existing Google task completed after the user confirms the chosen task.

    Args:
        task_id: Actual task ID returned by list_tasks or create_task.
        task_list_id: ID of the list containing the task, or @default.

    Returns:
        A status and the updated task, or a friendly error if completion failed.
    """
    try:
        list_id = _identifier(task_list_id, "task list ID")
        item_id = _identifier(task_id, "task ID")
        service = get_tasks_service()
        task = service.tasks().patch(tasklist=list_id, task=item_id, body={"status": "completed"}).execute()
        return {"status": "success", "task": _task_summary(task)}
    except Exception as error:
        return _error_result(error)


def update_task(task_id: str, title: Optional[str] = None, notes: Optional[str] = None,
                due_date: Optional[str] = None, task_list_id: str = "@default") -> dict:
    """Change only supplied task details after confirmation; preserve all other fields.

    Args:
        task_id: Actual task ID returned by list_tasks or create_task.
        title: New non-empty title, or omit to keep the existing title.
        notes: New notes; empty text clears notes, omission leaves them unchanged.
        due_date: New YYYY-MM-DD date; empty text clears the date, omission keeps it.
        task_list_id: ID of the list containing the task, or @default.

    Returns:
        A status and the updated task, or a friendly validation or API error.
    """
    try:
        list_id = _identifier(task_list_id, "task list ID")
        item_id = _identifier(task_id, "task ID")
        body = {}
        if title is not None:
            body["title"] = _title(title)
        if notes is not None:
            body["notes"] = _notes(notes)
        if due_date is not None:
            body["due"] = _due_timestamp(due_date) if due_date != "" else None
        if not body:
            raise _InputError("Provide a title, notes, or due date to change.")
        service = get_tasks_service()
        task = service.tasks().patch(tasklist=list_id, task=item_id, body=body).execute()
        return {"status": "success", "task": _task_summary(task)}
    except Exception as error:
        return _error_result(error)


def delete_task(task_id: str, task_list_id: str = "@default") -> dict:
    """Delete a Google task only after the user explicitly confirms its exact identity.

    Args:
        task_id: Actual task ID returned by list_tasks or create_task.
        task_list_id: ID of the list containing the task, or @default.

    Returns:
        A success status and the deleted task ID, or a friendly error.
    """
    try:
        list_id = _identifier(task_list_id, "task list ID")
        item_id = _identifier(task_id, "task ID")
        service = get_tasks_service()
        service.tasks().delete(tasklist=list_id, task=item_id).execute()
        return {"status": "success", "task_id": item_id, "message": "Task deleted."}
    except Exception as error:
        return _error_result(error)


tasks_tools = [list_task_lists, list_tasks, create_task, complete_task, update_task, delete_task]
