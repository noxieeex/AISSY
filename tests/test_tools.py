
import json
import pytest
from datetime import date, datetime

from aissy.tools import (
    get_current_datetime,
    get_date,
    get_relative_date_offset,
    execute_tool,
    TOOL_DEFINITIONS,
)


def test_get_current_datetime_formats_given_date():
    now = datetime(2026, 11, 9, 17, 48)
    result = get_current_datetime(now)
    assert result == "2026-11-09T17:48:00"


def test_get_current_datetime_works_without_arguments():
    result = get_current_datetime()
    parsed = datetime.fromisoformat(result)
    assert isinstance(parsed, datetime)
    assert parsed.tzinfo is not None


def test_get_date_returns_tomorrow():
    today = date(2026, 11, 9)
    result = get_date(1, today)

    assert result == {
        "date": "2026-11-10",
        "weekday": "terça-feira",
        "weekday_index": 1,
    }


def test_get_date_returns_yesterday():
    today = date(2026, 11, 9)
    result = get_date(-1, today)

    assert result == {
        "date": "2026-11-08",
        "weekday": "domingo",
        "weekday_index": 6,
    }


def test_get_date_returns_today():
    today = date(2026, 11, 9)
    result = get_date(0, today)

    assert result == {
        "date": "2026-11-09",
        "weekday": "segunda-feira",
        "weekday_index": 0,
    }


def test_get_date_rejects_boolean_offset():
    with pytest.raises(TypeError, match="integer"):
        get_date(True)


def test_datetime_tools_are_registered():
    names = [tool["function"]["name"] for tool in TOOL_DEFINITIONS]
    assert {"get_current_datetime", "get_date"} <= set(names)


def test_execute_tool_calls_datetime_function():
    result = execute_tool("get_current_datetime")
    parsed = datetime.fromisoformat(result)
    assert isinstance(parsed, datetime)


def test_execute_tool_calls_get_date():
    result = execute_tool("get_date", {"days_offset": 1})
    parsed = json.loads(result)

    assert "date" in parsed
    assert "weekday" in parsed
    assert "weekday_index" in parsed


def test_execute_tool_rejects_unknown_tools():
    with pytest.raises(ValueError, match="Unknown tool"):
        execute_tool("delete_everything")


def test_execute_tool_rejects_invalid_arguments():
    with pytest.raises(TypeError, match="dictionary"):
        execute_tool("get_date", "invalid")


def test_execute_tool_rejects_missing_date_arguments():
    with pytest.raises(ValueError, match="days_offset"):
        execute_tool("get_date", {})


def test_execute_tool_rejects_unexpected_datetime_arguments():
    with pytest.raises(ValueError, match="Unexpected arguments"):
        execute_tool("get_current_datetime", {"command": "something"})


# Relative date detection

def test_detects_tomorrow():
    assert get_relative_date_offset("E amanhã?") == 1


def test_detects_yesterday():
    assert get_relative_date_offset("Que dia foi ontem?") == -1


def test_detects_day_after_tomorrow():
    assert get_relative_date_offset("E depois de amanhã?") == 2


def test_detects_days_from_now():
    assert get_relative_date_offset(
        "Que dia da semana cai daqui a 10 dias?"
    ) == 10


def test_detects_days_in_future():
    assert get_relative_date_offset("E em 5 dias?") == 5


def test_detects_days_in_past():
    assert get_relative_date_offset("E há 3 dias?") == -3


def test_ignores_messages_without_relative_dates():
    assert get_relative_date_offset("Como você está?") is None

