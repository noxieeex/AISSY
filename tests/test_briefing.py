from datetime import datetime

import pytest

from aissy.briefing import build_briefing
from aissy.tasks import TaskStore


@pytest.fixture
def store():
    task_store = TaskStore(":memory:")
    yield task_store
    task_store.close()


# 12/11/2026 é quinta-feira.
MORNING = datetime(2026, 11, 12, 8, 0)


def test_empty_briefing_says_free_day(store):
    text = build_briefing(store, MORNING)

    assert "Bom dia" in text
    assert "quinta-feira" in text
    assert "12/11/2026" in text
    assert "Dia livre" in text


def test_greeting_changes_with_hour(store):
    assert "Boa tarde" in build_briefing(store, datetime(2026, 11, 12, 15))
    assert "Boa noite" in build_briefing(store, datetime(2026, 11, 12, 21))


def test_name_is_used_in_greeting(store):
    assert "Bom dia, Ge!" in build_briefing(store, MORNING, name="Ge")


def test_briefing_groups_tasks(store):
    store.add_task("atrasada", "2026-11-10")
    store.add_task("reunião", "2026-11-12T14:30")
    store.add_task("ideia")
    store.add_task("futura", "2026-12-01")

    text = build_briefing(store, MORNING)

    assert "Atrasadas:" in text and "atrasada" in text
    assert "Para hoje:" in text and "reunião (às 14:30)" in text
    assert "Sem prazo:" in text and "ideia" in text
    assert "futura" not in text
