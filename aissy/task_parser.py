import re
from datetime import timedelta

WEEKDAY_INDEX = {
    "segunda": 0, "terça": 1, "terca": 1, "quarta": 2,
    "quinta": 3, "sexta": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}

TIMER_PATTERN = (
    r"^(?:por favor,?\s*)?(?:(?:um|uma)\s+)?(?:timer|cronômetro|cronometro|"
    r"alarme)\s+(?:de|para|pra|em|for)\s+(.+)$"
)

REQUEST_PATTERNS = (
    r"^(?:por favor,?\s*)?me\s+(?:lembr[ae]|avis[ae])\s+(?:de\s+|que\s+)?(.+)$",
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


NUMBER_WORDS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "meia": 0.5}

DURATION_PATTERN = (
    r"\b(?:daqui\s+a|em|in|de|for)?\s*(\d+|um|uma|dois|duas)\s*"
    r"(minutos?|mins?|horas?|hs?|minutes?|hours?)\b"
)


def _find_duration(text):
    """Devolve (minutos, trecho) para 'em 20 minutos', '2 horas'..."""
    match = re.search(r"\bem\s+meia\s+hora\b", text, re.IGNORECASE)

    if match:
        return 30, match

    match = re.search(DURATION_PATTERN, text, re.IGNORECASE)

    if not match:
        return None, None

    amount = match.group(1).lower()
    amount = int(amount) if amount.isdigit() else NUMBER_WORDS[amount]
    unit = match.group(2).lower()
    minutes = amount * (60 if unit.startswith("h") else 1)

    if minutes <= 0 or minutes > 24 * 60:
        return None, None

    return int(minutes), match


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


def parse_task_request(text, today, now=None):
    """
    Interpreta pedidos como 'me lembra de X amanhã às 10h'.
    Devolve {"title": ..., "due": ...} ou None se não for um pedido de tarefa.
    """
    if not isinstance(text, str):
        return None

    remainder = None
    is_timer = False

    timer_match = re.match(TIMER_PATTERN, text.strip(), re.IGNORECASE)

    if timer_match:
        remainder = timer_match.group(1).strip().rstrip(".!?")
        is_timer = True

    for pattern in () if is_timer else REQUEST_PATTERNS:
        match = re.match(pattern, text.strip(), re.IGNORECASE)

        if match:
            remainder = match.group(1).strip().rstrip(".!?")
            break

    if not remainder:
        return None

    # "em 20 minutos" / "timer de 25 minutos": precisa saber que horas são.
    if now is not None:
        minutes, duration_match = _find_duration(remainder)

        if minutes:
            due_at = (now + timedelta(minutes=minutes)).replace(
                second=0, microsecond=0
            )
            start, end = duration_match.span()
            rest = (remainder[:start] + " " + remainder[end:])
            title = re.sub(r"\s+", " ", rest).strip(" ,.;:-")
            title = re.sub(
                r"\s+(?:para|pra|na|no|em|de|às|as|a|on|at|for)$",
                "",
                title,
                flags=re.IGNORECASE,
            )

            if not title:
                title = "Timer"

            title = title[0].upper() + title[1:]

            return {
                "title": title,
                "due": due_at.isoformat(timespec="minutes"),
                "minutes": minutes,
            }

    if is_timer:
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
