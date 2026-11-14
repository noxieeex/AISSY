# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import json
from datetime import datetime

import pytest

from aissy.apps import AppLauncher
from aissy.conversation import Conversation
from aissy.reminders import collect_due_reminders
from aissy.safety import MemoryAuditLog, Policy, SafetyLayer
from aissy.tasks import TaskStore
from aissy.tools import TOOL_DEFINITIONS, execute_tool

NOW = datetime(2026, 11, 12, 10, 0)


@pytest.fixture
def store():
    task_store = TaskStore(":memory:")
    yield task_store
    task_store.close()


# ---------- lembretes no horário ----------

def test_reminder_fires_once_when_due(store):
    store.add_task("ligar pro dentista", "2026-11-12T09:58")

    first = collect_due_reminders(store, NOW, "Ge")
    second = collect_due_reminders(store, NOW, "Ge")

    assert first == ["Ge, lembrete: ligar pro dentista!"]
    assert second == []


def test_reminder_not_fired_before_time(store):
    store.add_task("reunião", "2026-11-12T10:30")

    assert collect_due_reminders(store, NOW) == []


def test_old_missed_reminder_is_left_for_the_briefing(store):
    store.add_task("antigo", "2026-11-12T08:00")

    assert collect_due_reminders(store, NOW) == []
    assert len(store.list_tasks()) == 1


def test_date_only_tasks_never_fire(store):
    store.add_task("sem hora", "2026-11-12")

    assert collect_due_reminders(store, NOW) == []


def test_done_tasks_do_not_fire(store):
    task = store.add_task("feito", "2026-11-12T09:59")
    store.complete_task(task["id"])

    assert collect_due_reminders(store, NOW) == []


def test_message_without_name(store):
    store.add_task("beber água", "2026-11-12T10:00")

    assert collect_due_reminders(store, NOW) == ["Lembrete: beber água!"]


def test_old_database_gets_the_notified_column(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, due TEXT, done INTEGER NOT NULL DEFAULT 0, "
        "created_at TEXT NOT NULL, completed_at TEXT)"
    )
    connection.execute(
        "INSERT INTO tasks (title, due, created_at) VALUES ('velha', "
        "'2026-11-12T09:59', 'x')"
    )
    connection.commit()
    connection.close()

    migrated = TaskStore(path)

    assert [t["title"] for t in migrated.due_reminders(NOW)] == ["velha"]
    migrated.close()


# ---------- abrir apps ----------

class Opened:
    def __init__(self):
        self.targets = []

    def __call__(self, target):
        self.targets.append(target)


@pytest.fixture
def launcher():
    opened = Opened()
    instance = AppLauncher(opener=opened, config_path="nao-existe.json")
    instance.opened = opened
    return instance


@pytest.fixture
def safety(launcher):
    return SafetyLayer(Policy(allowed_apps=launcher.names()), MemoryAuditLog())


def test_opens_allowed_app_with_aliases(launcher):
    assert launcher.open("o Spotify") == "spotify"
    assert launcher.open("navegador") == "chrome"
    assert launcher.opened.targets == ["spotify:", "chrome"]


def test_unknown_app_is_refused(launcher):
    with pytest.raises(ValueError):
        launcher.open("format c:")

    assert launcher.opened.targets == []


def test_find_ignores_non_strings(launcher):
    assert launcher.find(None) is None
    assert launcher.find(42) is None


def test_user_config_adds_apps(tmp_path):
    config = tmp_path / "apps.json"
    config.write_text(json.dumps({"Meu Jogo": "C:/jogos/jogo.exe", "x": 1}))

    launcher = AppLauncher(opener=Opened(), config_path=config)

    assert launcher.find("meu jogo") == "meu jogo"
    assert launcher.find("x") is None


@pytest.mark.parametrize(
    "content",
    [
        "{não é json".encode("utf-8"),
        b"{n\xe3o \xe9 json",  # texto salvo em ANSI (cp1252), não UTF-8
        "[1, 2, 3]".encode("utf-8"),
    ],
)
def test_broken_user_config_is_ignored(tmp_path, content):
    config = tmp_path / "apps.json"
    config.write_bytes(content)

    launcher = AppLauncher(opener=Opened(), config_path=config)

    assert "spotify" in launcher.names()


def test_open_app_tool_is_declared_and_works(launcher, safety):
    names = {t["function"]["name"] for t in TOOL_DEFINITIONS}

    assert "open_app" in names
    assert json.loads(
        execute_tool(
            "open_app",
            {"name": "calculadora"},
            app_launcher=launcher,
            safety=safety,
        )
    ) == {"opened": "calculadora"}


@pytest.mark.parametrize(
    "arguments", [{}, {"name": 1}, {"name": "x", "extra": 1}, {"name": "hack"}]
)
def test_open_app_tool_rejects_bad_input(launcher, safety, arguments):
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        execute_tool(
            "open_app", arguments, app_launcher=launcher, safety=safety
        )

    assert launcher.opened.targets == []


def test_open_app_tool_without_launcher_raises():
    with pytest.raises(RuntimeError):
        execute_tool("open_app", {"name": "calculadora"})


# ---------- na conversa ----------

@pytest.fixture(autouse=True)
def isolate_memory(monkeypatch):
    class FakeMemory:
        def __init__(self, new_conversation=False):
            self.messages = []

        def load(self):
            return []

        def save(self, messages):
            self.messages = messages.copy()

    class FakeLongTerm:
        def search_memories(self, query, limit=5):
            return []

    monkeypatch.setattr("aissy.conversation.Memory", FakeMemory)
    monkeypatch.setattr("aissy.conversation.LongTermMemory", FakeLongTerm)


class NoLLM:
    def generate(self, messages):
        raise AssertionError("o modelo não deveria ser chamado")


def test_open_request_is_handled_in_code(launcher, safety):
    chat = Conversation("system", app_launcher=launcher, safety=safety)

    answer = chat.send_message("abre o spotify", NoLLM())

    assert answer == "Abrindo spotify!"
    assert launcher.opened.targets == ["spotify:"]


def test_open_request_in_english(launcher, safety):
    chat = Conversation("system", app_launcher=launcher, safety=safety)

    assert chat.send_message("open spotify", NoLLM()) == "Opening spotify!"


def test_open_request_for_unknown_app_goes_to_the_model(launcher, safety):
    class LLM:
        def generate(self, messages):
            return "Não posso abrir isso."

    chat = Conversation("system", app_launcher=launcher, safety=safety)

    assert chat.send_message("abre o terminal do sistema", LLM()) == "Não posso abrir isso."
    assert launcher.opened.targets == []


def test_open_failure_is_reported(launcher, safety):
    def broken(target):
        raise RuntimeError("Abrir aplicativos só funciona no Windows.")

    launcher.opener = broken
    chat = Conversation("system", app_launcher=launcher, safety=safety)

    assert "Não consegui abrir" in chat.send_message("abre o spotify", NoLLM())
