from datetime import datetime

DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_current_datetime(now=None):
    if now is None:
        now = datetime.now()

    day_name = DAYS_OF_WEEK[now.weekday()]
    return f"{day_name}, {now.strftime('%Y-%m-%d, %H:%M')}"