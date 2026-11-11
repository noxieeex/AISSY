import re
from datetime import timedelta

WEEKDAY_INDEX = {
    "segunda": 0, "terça": 1, "terca": 1, "quarta": 2,
    "quinta": 3, "sexta": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}

REQUEST_PATTERNS = (
    r"^(?:por favor,?\s*)?me\s+lembr[ae]\s+(?:de\s+|que\s+)?(.+)$",
    r"^(?:por favor,?\s*)?(?:anota|anote|adiciona|adicione|cria|crie)"
    r"\s+(?:uma\s+)?(?:tarefa|lembrete)(?:\s+(?:de|para|pra))?\s*:?\s*(.+)$",
    r"^(?:please\s+)?remind\s+me\s+(?:to\s+)?(.+)$",
    r"^(?:please\s+)?add\s+(?:a\s+)?(?:task|reminder)(?:\s+to)?\s*:?\s*(.+)$",
)

RELATIVE_DAYS = (
    (r"depois\s+de\s+amanh[ãa]|day\s+after\s+tomorrow", 2),
    (r"amanh[ãa]|tomorrow", 1),
    (r"hoje|today", 0),
)

TIME_PATTERN = (
    r"\b(?:às|as|at)\s+(\d{1,2})(?:\s*h\s*(\d{2})?|:(\d{2}))?"
    r"(?:\s*(am|pm))?\b(?:\s*horas?)?"
)


def _find_day(text, today):
    """Devolve (data, trecho_encontrado) ou (None, None)."""
    for pattern, offset in RELATIVE_DAYS:
        match = re.search(rf"\b(?:{pattern})\b", text, re.IGNORECASE)
        if match:
            return today + timedelta(days=offset), match

    match = re.search(
        r"\b(?:daqui\s+a|em|in)\s+(\d+)\s+(?:dias?|days?)\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return today + timedelta(days=int(match.group(1))), match

    names = "|".join(WEEKDAY_INDEX)
    match = re.search(
        rf"\b(?:(?:na|no|nesta|neste|esta|este|próxima|proxima|próximo|"
        rf"proximo)\s+)?({names})(?:-feira)?\b",
        text,
        re.IGNORECASE,
    )
    if match:
        target = WEEKDAY_INDEX[match.group(1).lower()]
        days_ahead = (target - today.weekday()) % 7 or 7
        return today + timedelta(days=days_ahead), match

    return None, None


def _find_time(text):
    match = re.search(TIME_PATTERN, text, re.IGNORECASE)

    if not match:
        return None, None

    hour = int(match.group(1))
    minute = int(match.group(2) or match.group(3) or 0)
    meridiem = (match.group(4) or "").lower()

    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    if hour > 23 or minute > 59:
        return None, None

    return (hour, minute), match


def parse_task_request(text, today):
    """
    Interpreta pedidos como 'me lembra de X amanhã às 10h'.
    Devolve {"title": ..., "due": ...} ou None se não for um pedido de tarefa.
    """
    if not isinstance(text, str):
        return None

    remainder = None

    for pattern in REQUEST_PATTERNS:
        match = re.match(pattern, text.strip(), re.IGNORECASE)

        if match:
            remainder = match.group(1).strip().rstrip(".!?")
            break

    if not remainder:
        return None

    day, day_match = _find_day(remainder, today)
    clock, time_match = _find_time(remainder)

    spans = [m.span() for m in (day_match, time_match) if m]

    for start, end in sorted(spans, reverse=True):
        remainder = remainder[:start] + " " + remainder[end:]

    title = re.sub(r"\s+", " ", remainder).strip(" ,.;:-")
    title = re.sub(
        r"\s+(?:para|pra|na|no|em|de|às|as|a|on|at|for)$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    if not title:
        return None

    title = title[0].upper() + title[1:]

    due = None

    if clock and day is None:
        day = today

    if day:
        due = day.isoformat()

        if clock:
            due += f"T{clock[0]:02d}:{clock[1]:02d}"

    return {"title": title, "due": due}
