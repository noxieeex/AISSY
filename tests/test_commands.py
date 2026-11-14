# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

from datetime import datetime

import pytest

from aissy.commands import handle_command
from aissy.tasks import TaskStore


NOW = datetime(2026, 11, 12, 8, 0)


@pytest.fixture
def store():
    task_store = TaskStore(":memory:")
    yield task_store
    task_store.close()


def test_plain_text_is_not_a_command(store):
    assert handle_command("oi tudo bem?", store, NOW) is None
    assert handle_command("   ", store, NOW) is None


def test_new_and_unknown_commands_are_left_to_the_caller(store):
    assert handle_command("/new", store, NOW) is None
    assert handle_command("/xyz", store, NOW) is None


def test_hoje_returns_briefing(store):
    assert "Bom dia" in handle_command("/hoje", store, NOW)


def test_tarefas_lists_pending(store):
    assert "Nenhuma tarefa" in handle_command("/tarefas", store, NOW)

    store.add_task("estudar", "2026-11-13T10:00")

    text = handle_command("/tarefas", store, NOW)

    assert "#1 estudar" in text and "2026-11-13 10:00" in text


def test_feito_and_apagar(store):
    first = store.add_task("a")
    second = store.add_task("b")

    assert "concluída" in handle_command(f"/feito {first['id']}", store, NOW)
    assert "Não encontrei" in handle_command(f"/feito {first['id']}", store, NOW)
    assert "apagada" in handle_command(f"/apagar {second['id']}", store, NOW)
    assert store.list_tasks() == []


@pytest.mark.parametrize("text", ["/feito", "/feito abc", "/apagar"])
def test_commands_with_bad_argument_explain_usage(store, text):
    assert "Use assim" in handle_command(text, store, NOW)


def test_ajuda_lists_commands(store):
    assert "/tarefas" in handle_command("/ajuda", store, NOW)
