import json
from datetime import datetime

import pytest

from aissy.conversation import Conversation
from aissy.safety import MemoryAuditLog, Policy, SafetyLayer
from aissy.tasks import TaskStore
from aissy.tools import TOOL_DEFINITIONS, execute_tool


def make_safety():
    return SafetyLayer(Policy(), MemoryAuditLog())


@pytest.fixture
def safety():
    return make_safety()


@pytest.fixture
def store():
    task_store = TaskStore(":memory:")
    yield task_store
    task_store.close()


# ---------- execute_tool ----------

def test_task_tools_are_declared():
    names = {tool["function"]["name"] for tool in TOOL_DEFINITIONS}

    assert {"add_task", "list_tasks", "complete_task"} <= names


def test_add_list_complete_via_tools(store, safety):
    added = json.loads(
        execute_tool(
            "add_task",
            {"title": "pagar conta", "due": "2026-11-13"},
            task_store=store,
            safety=safety,
        )
    )
    assert added["title"] == "pagar conta"

    listed = json.loads(execute_tool("list_tasks", {}, task_store=store, safety=safety))
    assert [t["title"] for t in listed] == ["pagar conta"]

    done = json.loads(
        execute_tool(
            "complete_task", {"task_id": added["id"]}, task_store=store, safety=safety
        )
    )
    assert done == {"completed": added["id"]}
    assert json.loads(execute_tool("list_tasks", {}, task_store=store, safety=safety)) == []


def test_task_tool_without_store_raises(safety):
    with pytest.raises(RuntimeError):
        execute_tool("list_tasks", {}, safety=safety)


def test_task_tool_without_safety_layer_is_blocked(store):
    with pytest.raises(RuntimeError, match="Blocked by safety layer"):
        execute_tool("list_tasks", {}, task_store=store)


@pytest.mark.parametrize(
    "name, arguments",
    [
        ("add_task", {}),
        ("add_task", {"title": "x", "extra": 1}),
        ("add_task", {"title": "x", "due": "amanhã"}),
        ("list_tasks", {"x": 1}),
        ("complete_task", {}),
        ("complete_task", {"task_id": "1"}),
        ("complete_task", {"task_id": True}),
        ("complete_task", {"task_id": 999}),
    ],
)
def test_task_tools_reject_bad_arguments(store, safety, name, arguments):
    with pytest.raises((ValueError, TypeError)):
        execute_tool(name, arguments, task_store=store, safety=safety)


def test_date_tools_still_work():
    assert execute_tool("get_current_datetime", {})
    assert json.loads(execute_tool("get_date", {"days_offset": 1}))["date"]


# ---------- laço de tool calling na Conversation ----------

@pytest.fixture(autouse=True)
def isolate_memory(monkeypatch):
    class FakeMemory:
        def __init__(self, new_conversation=False):
            self.messages = []

        def load(self):
            return self.messages.copy()

        def save(self, messages):
            self.messages = messages.copy()

    class FakeLongTerm:
        def search_memories(self, query, limit=5):
            return []

    monkeypatch.setattr("aissy.conversation.Memory", FakeMemory)
    monkeypatch.setattr("aissy.conversation.LongTermMemory", FakeLongTerm)


def tool_call(name, arguments, call_id="call_1"):
    return {
        "id": call_id,
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


class ScriptedLLM:
    """Devolve respostas prontas e guarda as mensagens que recebeu."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def generate_with_tools(self, messages, tools):
        self.seen.append([m.copy() for m in messages])
        return self.replies.pop(0)


NOW = datetime(2026, 11, 12, 9, 0)


def make_conversation(store):
    return Conversation(
        "system",
        task_store=store,
        now_fn=lambda: NOW,
        safety=make_safety(),
    )


def test_model_can_add_a_task_through_the_loop(store):
    llm = ScriptedLLM([
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                tool_call("add_task", {"title": "ligar pro dentista"})
            ],
        },
        {"role": "assistant", "content": "Anotado!", "tool_calls": []},
    ])

    answer = make_conversation(store).send_message(
        "não esquece de ligar pro dentista", llm
    )

    assert answer == "Anotado!"
    assert [t["title"] for t in store.list_tasks()] == ["ligar pro dentista"]


def test_tool_error_goes_back_to_the_model_instead_of_crashing(store):
    llm = ScriptedLLM([
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                tool_call("add_task", {"title": "x", "due": "amanhã"})
            ],
        },
        {"role": "assistant", "content": "Não deu certo.", "tool_calls": []},
    ])

    answer = make_conversation(store).send_message("preciso fazer x amanhã", llm)

    tool_message = llm.seen[1][-1]

    assert answer == "Não deu certo."
    assert tool_message["role"] == "tool"
    assert "error" in json.loads(tool_message["content"])
    assert store.list_tasks() == []


def test_unknown_tool_and_bad_json_become_errors(store):
    llm = ScriptedLLM([
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                tool_call("hack", {}, "a"),
                {"id": "b", "function": {"name": "list_tasks",
                                         "arguments": "{not json"}},
            ],
        },
        {"role": "assistant", "content": "ok", "tool_calls": []},
    ])

    make_conversation(store).send_message("oi", llm)

    results = [m for m in llm.seen[1] if m["role"] == "tool"]

    assert len(results) == 2
    assert all("error" in json.loads(m["content"]) for m in results)


def test_current_date_is_in_the_system_context(store):
    llm = ScriptedLLM([
        {"role": "assistant", "content": "oi!", "tool_calls": []},
    ])

    make_conversation(store).send_message("oi", llm)

    system = llm.seen[0][0]["content"]

    assert "quinta-feira" in system
    assert "2026-11-12 09:00" in system


def test_spanish_message_gets_spanish_instruction(store):
    llm = ScriptedLLM([
        {"role": "assistant", "content": "¡Hola!", "tool_calls": []},
    ])

    make_conversation(store).send_message("hola, necesito ayuda por favor", llm)

    assert "español" in llm.seen[0][0]["content"]


# ---------- pedidos tratados em código e trava contra "anotei" falso ----------

def test_reminder_request_is_saved_without_calling_the_model(store):
    llm = ScriptedLLM([])

    answer = make_conversation(store).send_message(
        "me lembra de ligar pro dentista amanhã às 10h", llm
    )

    assert llm.seen == []
    assert "Anotado" in answer and "10:00" in answer
    assert store.list_tasks()[0]["due"] == "2026-11-13T10:00"


def test_english_reminder_gets_english_confirmation(store):
    answer = make_conversation(store).send_message(
        "remind me to call mom tomorrow", ScriptedLLM([])
    )

    assert answer.startswith("Done!")


def test_false_claim_of_saving_is_replaced(store):
    llm = ScriptedLLM([
        {
            "role": "assistant",
            "content": "Anotei seu lembrete no calendário!",
            "tool_calls": [],
        },
    ])

    answer = make_conversation(store).send_message(
        "não esquece de me avisar da reunião", llm
    )

    assert "Não consegui salvar" in answer
    assert store.list_tasks() == []


def test_claim_is_kept_when_the_tool_really_ran(store):
    llm = ScriptedLLM([
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [tool_call("add_task", {"title": "reunião"})],
        },
        {"role": "assistant", "content": "Anotei o lembrete!", "tool_calls": []},
    ])

    answer = make_conversation(store).send_message(
        "não esquece de me avisar da reunião", llm
    )

    assert answer == "Anotei o lembrete!"
    assert len(store.list_tasks()) == 1
