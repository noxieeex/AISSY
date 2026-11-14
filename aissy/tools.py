# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import json
import re
from datetime import date, datetime, timedelta

from aissy.safety import Action, Origin, guard


WEEKDAYS_PT = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def get_current_datetime(now=None):
    if now is None:
        now = datetime.now().astimezone()
    return now.isoformat(timespec="seconds")


def get_date(days_offset, today=None):
    if isinstance(days_offset, bool) or not isinstance(days_offset, int):
        raise TypeError("days_offset must be an integer.")

    if today is None:
        today = datetime.now().date()

    target_date = today + timedelta(days=days_offset)

    return {
        "date": target_date.isoformat(),
        "weekday": WEEKDAYS_PT[target_date.weekday()],
        "weekday_index": target_date.weekday(),
    }


def get_relative_date_offset(message):
    """
    Identifica referências explícitas a datas relativas em português.
    Retorna o deslocamento em dias ou None quando não encontra uma.
    """
    if not isinstance(message, str):
        return None

    text = message.lower()

    fixed_dates = (
        (r"\bdepois de amanh[ãa]\b", 2),
        (r"\banteontem\b", -2),
        (r"\bamanh[ãa]\b", 1),
        (r"\bontem\b", -1),
        (r"\bhoje\b", 0),
    )

    for pattern, offset in fixed_dates:
        if re.search(pattern, text):
            return offset

    number = r"(\d+)"
    patterns = (
        (rf"\bdaqui\s+a\s+{number}\s+dias?\b", 1),
        (rf"\bem\s+{number}\s+dias?\b", 1),
        (rf"\bhá\s+{number}\s+dias?\b", -1),
        (rf"\b{number}\s+dias?\s+atrás\b", -1),
    )

    for pattern, direction in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)) * direction

    return None

def is_date_question(message):
    """Detecta perguntas diretas sobre a data, em português."""
    if not isinstance(message, str):
        return False

    text = message.lower()

    patterns = (
        r"\bque dia (?:é|foi|será|vai ser|da semana)\b",
        r"\bqual (?:é )?a data\b",
        r"\bqual (?:é )?o dia\b",
        r"\bque data\b",
    )

    return any(re.search(pattern, text) for pattern in patterns)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": (
                "Get the exact current local date and time from the computer. "
                "Use whenever the user asks about the current time or date."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": (
                "Get the exact calendar date and weekday for a day relative "
                "to today. Use for tomorrow, yesterday, next week, days ago, "
                "or any relative date. weekday_index uses Monday=0, Sunday=6."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days_offset": {
                        "type": "integer",
                        "description": (
                            "Number of days relative to today. "
                            "0=today, 1=tomorrow, -1=yesterday."
                        ),
                    }
                },
                "required": ["days_offset"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": (
                "Open an application on the user's computer, such as "
                "Spotify, Steam, Chrome or the calculator. Only apps from "
                "the allowed list can be opened."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the app, e.g. 'spotify'.",
                    }
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": (
                "Save a task or reminder for the user. Use when the user asks "
                "to be reminded of something or to add something to their "
                "to-do list. If they mention a day, call get_date first and "
                "pass the resulting date in due."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short description of the task.",
                    },
                    "due": {
                        "type": "string",
                        "description": (
                            "Optional deadline: YYYY-MM-DD, or "
                            "YYYY-MM-DDTHH:MM when a time is given."
                        ),
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": (
                "List the user's pending tasks and reminders, with ids. "
                "Use when the user asks what they have to do."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": (
                "Mark a task as done by its id. Call list_tasks first if "
                "you do not know the id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Id of the task, from list_tasks.",
                    }
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
]


TOOL_FUNCTIONS = {
    "get_current_datetime": get_current_datetime,
    "get_date": get_date,
}


TASK_TOOLS = {"add_task", "list_tasks", "complete_task"}


def build_open_app_action(app_launcher, name, origin):
    """Ação 'abrir app' no formato que a Safety Layer avalia."""
    key = app_launcher.find(name) or str(name).strip().lower()

    return Action(
        kind="app",
        operation="open",
        origin=origin,
        target=key,
        args={"launch": app_launcher.apps.get(key, "")},
    )


def _prepare_task_tool(name, arguments, task_store, origin):
    """Valida os argumentos e devolve (ação, executor)."""
    if task_store is None:
        raise RuntimeError("Task storage is not available.")

    if name == "add_task":
        allowed = {"title", "due"}

        if "title" not in arguments or not set(arguments) <= allowed:
            raise ValueError("add_task requires title and accepts only due.")

        title, due = arguments["title"], arguments.get("due")

        return (
            Action("task", "create", origin, args={"title": title, "due": due}),
            lambda: task_store.add_task(title, due),
        )

    if name == "list_tasks":
        if arguments:
            raise ValueError("Unexpected arguments for list_tasks.")

        return (
            Action("task", "read", origin),
            lambda: task_store.list_tasks(),
        )

    if set(arguments) != {"task_id"}:
        raise ValueError("complete_task requires only task_id.")

    task_id = arguments["task_id"]

    if isinstance(task_id, bool) or not isinstance(task_id, int):
        raise TypeError("task_id must be an integer.")

    def complete():
        if not task_store.complete_task(task_id):
            raise ValueError(f"No pending task with id {task_id}.")

        return {"completed": task_id}

    return Action("task", "complete", origin, target=str(task_id)), complete


def _prepare_open_app(arguments, app_launcher, origin):
    if app_launcher is None:
        raise RuntimeError("Opening apps is not available.")

    if set(arguments) != {"name"} or not isinstance(arguments["name"], str):
        raise ValueError("open_app requires only a text name.")

    name = arguments["name"]

    return (
        build_open_app_action(app_launcher, name, origin),
        lambda: {"opened": app_launcher.open(name)},
    )


def execute_tool(
    name,
    arguments=None,
    task_store=None,
    app_launcher=None,
    safety=None,
    origin=Origin.MODEL,
):
    """
    Funções puras (data e hora) rodam direto: não tocam em nenhum recurso.
    Ferramentas com efeito (tarefas, abrir apps) só executam através da
    Safety Layer; sem ela, são bloqueadas.
    """
    if name not in TOOL_FUNCTIONS and name not in TASK_TOOLS and name != "open_app":
        raise ValueError(f"Unknown tool: {name}")

    if arguments is None:
        arguments = {}

    if not isinstance(arguments, dict):
        raise TypeError("Tool arguments must be a dictionary.")

    if name == "open_app":
        action, executor = _prepare_open_app(arguments, app_launcher, origin)
        result = guard(safety, action, executor)
    elif name in TASK_TOOLS:
        action, executor = _prepare_task_tool(name, arguments, task_store, origin)
        result = guard(safety, action, executor)
    else:
        if name == "get_current_datetime" and arguments:
            raise ValueError("Unexpected arguments for get_current_datetime.")

        if name == "get_date" and set(arguments) != {"days_offset"}:
            raise ValueError("get_date requires only days_offset.")

        result = TOOL_FUNCTIONS[name](**arguments)

    if isinstance(result, (dict, list)):
        return json.dumps(result, ensure_ascii=False)

    return str(result)
