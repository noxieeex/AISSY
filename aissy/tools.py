import json
import re
from datetime import date, datetime, timedelta


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
]


TOOL_FUNCTIONS = {
    "get_current_datetime": get_current_datetime,
    "get_date": get_date,
}


def execute_tool(name, arguments=None):
    if name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown tool: {name}")

    if arguments is None:
        arguments = {}

    if not isinstance(arguments, dict):
        raise TypeError("Tool arguments must be a dictionary.")

    if name == "get_current_datetime" and arguments:
        raise ValueError("Unexpected arguments for get_current_datetime.")

    if name == "get_date" and set(arguments) != {"days_offset"}:
        raise ValueError("get_date requires only days_offset.")

    result = TOOL_FUNCTIONS[name](**arguments)

    if isinstance(result, (dict, list)):
        return json.dumps(result, ensure_ascii=False)

    return str(result)
