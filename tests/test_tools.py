from datetime import datetime

from aissy.tools import get_current_datetime


def test_get_current_datetime_formats_given_date():
    fixed = datetime(2026, 11, 9, 17, 48)

    assert get_current_datetime(fixed) == "Monday, 2026-11-09, 17:48"


def test_get_current_datetime_handles_sunday():
    fixed = datetime(2026, 11, 15, 9, 5)

    assert get_current_datetime(fixed) == "Sunday, 2026-11-15, 09:05"


def test_get_current_datetime_works_without_arguments():
    result = get_current_datetime()

    assert isinstance(result, str)
    assert str(datetime.now().year) in result
    assert ":" in result