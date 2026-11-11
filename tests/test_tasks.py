from datetime import date

import pytest

from aissy.tasks import TaskStore, parse_due


@pytest.fixture
def store():
    task_store = TaskStore(":memory:")
    yield task_store
    task_store.close()


def test_add_and_list_task(store):
    task = store.add_task("Estudar inglês")

    assert task["id"] == 1
    assert task["done"] is False
    assert store.list_tasks() == [task]


def test_add_task_rejects_empty_title(store):
    with pytest.raises(ValueError):
        store.add_task("   ")


def test_parse_due_accepts_date_and_datetime():
    assert parse_due("2026-11-12") == "2026-11-12"
    assert parse_due("2026-11-12T09:30") == "2026-11-12T09:30"
    assert parse_due(None) is None
    assert parse_due("  ") is None


@pytest.mark.parametrize("value", ["amanhã", "2026-13-40", "12/11/2026"])
def test_parse_due_rejects_invalid(value):
    with pytest.raises(ValueError):
        parse_due(value)


def test_parse_due_rejects_non_string():
    with pytest.raises(TypeError):
        parse_due(20261112)


def test_list_orders_by_due_then_without_due(store):
    store.add_task("sem prazo")
    store.add_task("depois", "2026-11-20")
    store.add_task("antes", "2026-11-11")

    titles = [task["title"] for task in store.list_tasks()]

    assert titles == ["antes", "depois", "sem prazo"]


def test_complete_task_hides_it_from_pending(store):
    task = store.add_task("lavar louça")

    assert store.complete_task(task["id"]) is True
    assert store.list_tasks() == []
    assert len(store.list_tasks(include_done=True)) == 1


def test_complete_twice_or_unknown_returns_false(store):
    task = store.add_task("x")
    store.complete_task(task["id"])

    assert store.complete_task(task["id"]) is False
    assert store.complete_task(999) is False


def test_delete_task(store):
    task = store.add_task("x")

    assert store.delete_task(task["id"]) is True
    assert store.delete_task(task["id"]) is False
    assert store.list_tasks(include_done=True) == []


def test_overdue_and_due_today(store):
    today = date(2026, 11, 12)
    store.add_task("atrasada", "2026-11-10")
    store.add_task("hoje", "2026-11-12T18:00")
    store.add_task("futura", "2026-11-15")
    store.add_task("sem prazo")

    assert [t["title"] for t in store.overdue_tasks(today)] == ["atrasada"]
    assert [t["title"] for t in store.tasks_due_on(today)] == ["hoje"]


def test_done_tasks_are_not_overdue(store):
    task = store.add_task("velha", "2026-01-01")
    store.complete_task(task["id"])

    assert store.overdue_tasks(date(2026, 11, 12)) == []


def test_tasks_persist_in_file(tmp_path):
    path = tmp_path / "sub" / "tasks.db"

    first = TaskStore(path)
    first.add_task("persistente")
    first.close()

    second = TaskStore(path)

    assert [t["title"] for t in second.list_tasks()] == ["persistente"]
    second.close()
