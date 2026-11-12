import ast
import json
from pathlib import Path

import pytest

from aissy.safety import (
    Action,
    ActionBlocked,
    Decision,
    FileAuditLog,
    MemoryAuditLog,
    Origin,
    Policy,
    SafetyLayer,
    Verdict,
    guard,
    is_stop_phrase,
)
from aissy.safety.policy import PERMANENTLY_DENIED_KINDS


def make_layer(apps=("spotify", "calculadora")):
    audit = MemoryAuditLog()
    return SafetyLayer(Policy(allowed_apps=apps), audit), audit


def open_app(name="spotify", origin=Origin.USER, launch="spotify:"):
    return Action("app", "open", origin, target=name, args={"launch": launch})


def task_create(origin=Origin.MODEL):
    return Action("task", "create", origin, args={"title": "x", "due": None})


class Counter:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return "done"


# ---------- allowlist ----------

def test_allowed_actions_execute_and_return_the_result():
    layer, _ = make_layer()
    run = Counter()

    assert layer.run(open_app(), run) == "done"
    assert run.calls == 1


def test_unknown_action_is_denied():
    layer, _ = make_layer()
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(Action("file", "read", Origin.MODEL, target="C:/x.txt"), run)

    assert blocked.value.decision.rule == "allowlist.unknown"
    assert run.calls == 0


def test_app_outside_the_allowed_list_is_denied():
    layer, _ = make_layer()
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(open_app("regedit", launch="regedit.exe"), run)

    assert blocked.value.decision.rule == "allowlist.app"
    assert run.calls == 0


def test_app_without_target_is_denied():
    layer, _ = make_layer()

    with pytest.raises(ActionBlocked):
        layer.run(Action("app", "open", Origin.USER), Counter())


# ---------- blocklist (inclui Riot / Vanguard) ----------

@pytest.mark.parametrize("kind", sorted(PERMANENTLY_DENIED_KINDS))
def test_permanently_forbidden_kinds_are_always_denied(kind):
    layer, _ = make_layer()
    run = Counter()

    for origin in Origin:
        with pytest.raises(ActionBlocked) as blocked:
            layer.run(Action(kind, "any", origin), run)

        assert blocked.value.decision.rule == "blocklist.kind"

    assert run.calls == 0


def test_forbidden_categories_cover_what_riot_prohibits():
    for kind in (
        "process_memory", "code_injection", "input_hook",
        "input_automation", "game_automation", "overlay", "screen_capture",
    ):
        assert kind in PERMANENTLY_DENIED_KINDS


@pytest.mark.parametrize(
    "name, launch",
    [
        ("valorant", "valorant.exe"),
        ("league of legends", "LeagueClient.exe"),
        ("meu jogo", "C:/Riot Games/Riot Client/RiotClientServices.exe"),
        ("vanguard", "vgc.exe"),
        ("qualquer", "C:/Program Files/Riot Vanguard/vgk.sys"),
    ],
)
def test_riot_and_vanguard_targets_are_protected_even_if_allowed(name, launch):
    layer, _ = make_layer(apps=(name,))
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(open_app(name, launch=launch), run)

    assert blocked.value.decision.rule == "blocklist.protected_target"
    assert run.calls == 0


def test_blocklist_beats_a_user_origin():
    layer, _ = make_layer(apps=("valorant",))

    with pytest.raises(ActionBlocked):
        layer.run(open_app("valorant", Origin.USER, "valorant.exe"), Counter())


@pytest.mark.parametrize(
    "target",
    ["data/apps.json", "C:/AISSY/data/audit.log", "aissy/safety/policy.py", ".env"],
)
def test_own_configuration_cannot_be_written(target):
    layer, _ = make_layer()

    for operation in ("write", "delete", "overwrite", "append"):
        with pytest.raises(ActionBlocked) as blocked:
            layer.run(Action("file", operation, Origin.MODEL, target=target), Counter())

        assert blocked.value.decision.rule == "blocklist.own_config"


# ---------- origem ----------

def test_external_content_has_no_authority():
    layer, _ = make_layer()
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(task_create(Origin.EXTERNAL), run)

    assert blocked.value.decision.rule == "origin.external"
    assert run.calls == 0


def test_invalid_origin_is_denied():
    layer, _ = make_layer()

    with pytest.raises(ActionBlocked):
        layer.run(Action("task", "create", "user"), Counter())


# ---------- fail closed ----------

def test_non_action_is_denied():
    layer, _ = make_layer()

    with pytest.raises(ActionBlocked):
        layer.run("apague tudo", Counter())


def test_policy_exception_blocks():
    class BrokenPolicy:
        def decide(self, action):
            raise RuntimeError("boom")

    layer = SafetyLayer(BrokenPolicy(), MemoryAuditLog())
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(task_create(), run)

    assert blocked.value.decision.rule == "policy.error"
    assert run.calls == 0


def test_invalid_policy_result_blocks():
    class WeirdPolicy:
        def decide(self, action):
            return True

    layer = SafetyLayer(WeirdPolicy(), MemoryAuditLog())

    with pytest.raises(ActionBlocked):
        layer.run(task_create(), Counter())


def test_confirm_verdict_blocks_while_confirmation_is_unavailable():
    class AskingPolicy:
        def decide(self, action):
            return Decision(Verdict.CONFIRM, "risky", "needs yes")

    layer = SafetyLayer(AskingPolicy(), MemoryAuditLog())
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(task_create(), run)

    assert blocked.value.decision.rule == "confirmation.unavailable"
    assert run.calls == 0


def test_no_audit_log_means_no_execution():
    layer = SafetyLayer(Policy(), audit=None)
    run = Counter()

    with pytest.raises(ActionBlocked):
        layer.run(task_create(), run)

    assert run.calls == 0


def test_audit_failure_blocks_and_keeps_blocking():
    class BrokenAudit:
        def record(self, entry):
            raise OSError("disk full")

    layer = SafetyLayer(Policy(), BrokenAudit())
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(task_create(), run)

    assert blocked.value.decision.rule == "audit.unavailable"
    assert layer.healthy is False
    assert run.calls == 0

    layer.audit = MemoryAuditLog()

    with pytest.raises(ActionBlocked):
        layer.run(task_create(), run)

    assert run.calls == 0


def test_failure_to_log_the_result_blocks_next_actions():
    class AuditFailsOnResult:
        def __init__(self):
            self.entries = []

        def record(self, entry):
            if entry["event"] == "result":
                raise OSError("disk full")

            self.entries.append(entry)

    layer = SafetyLayer(Policy(), AuditFailsOnResult())

    assert layer.run(task_create(), Counter()) == "done"

    with pytest.raises(ActionBlocked):
        layer.run(task_create(), Counter())


def test_guard_without_a_layer_blocks():
    run = Counter()

    with pytest.raises(ActionBlocked) as blocked:
        guard(None, task_create(), run)

    assert blocked.value.decision.rule == "layer.unavailable"
    assert run.calls == 0


def test_executor_errors_propagate_and_are_logged():
    layer, audit = make_layer()

    def failing():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        layer.run(task_create(), failing)

    assert audit.entries[-1]["result"] == "error: ValueError"


# ---------- auditoria ----------

def test_every_decision_is_logged_with_details():
    layer, audit = make_layer()
    layer.run(open_app(), Counter())

    with pytest.raises(ActionBlocked):
        layer.run(open_app("regedit", launch="regedit.exe"), Counter())

    events = [(e["event"], e.get("decision"), e.get("result")) for e in audit.entries]

    assert events == [
        ("decision", "allow", None),
        ("result", None, "ok"),
        ("decision", "deny", None),
    ]
    first = audit.entries[0]
    assert first["origin"] == "user" and first["kind"] == "app"
    assert first["operation"] == "open" and first["target"] == "spotify"
    assert first["rule"] == "allowlist" and first["ts"]


def test_long_arguments_are_truncated_in_the_log():
    layer, audit = make_layer()
    action = Action("task", "create", Origin.USER, args={"title": "x" * 1000})

    layer.run(action, Counter())

    assert len(audit.entries[0]["args"]["title"]) == 200


def test_file_audit_log_appends_json_lines(tmp_path):
    path = tmp_path / "logs" / "audit.log"
    layer = SafetyLayer(Policy(), FileAuditLog(path))

    layer.run(task_create(), Counter())
    layer.run(task_create(), Counter())

    lines = path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 4
    assert json.loads(lines[0])["event"] == "decision"


def test_audit_log_has_no_edit_or_delete_api():
    public = {n for n in dir(FileAuditLog) if not n.startswith("_")}

    assert public == {"record"}


# ---------- parada de emergência ----------

def test_emergency_stop_blocks_everything_until_resumed():
    layer, _ = make_layer()
    run = Counter()

    layer.halt()

    with pytest.raises(ActionBlocked) as blocked:
        layer.run(open_app(), run)

    assert blocked.value.decision.rule == "emergency.stopped"
    assert run.calls == 0

    layer.resume()

    assert layer.run(open_app(), run) == "done"


@pytest.mark.parametrize("text", ["Parar tudo!", "para tudo", "Emergência", "stop everything"])
def test_stop_phrases(text):
    assert is_stop_phrase(text)


@pytest.mark.parametrize("text", ["para de falar do trabalho", "oi", ""])
def test_normal_phrases_are_not_stop(text):
    assert not is_stop_phrase(text)


# ---------- verificação de inicialização ----------

def test_self_check_passes_with_a_working_layer():
    layer, audit = make_layer()

    assert layer.self_check() is True
    assert audit.entries[-1]["event"] == "self_check"


def test_self_check_fails_without_audit():
    assert SafetyLayer(Policy(), audit=None).self_check() is False


def test_self_check_fails_if_the_policy_allows_forbidden_things():
    class PermissivePolicy:
        def decide(self, action):
            return Decision(Verdict.ALLOW, "oops", "allow all")

    assert SafetyLayer(PermissivePolicy(), MemoryAuditLog()).self_check() is False


# ---------- arquitetura: nada contorna a camada ----------

AISSY_DIR = Path(__file__).resolve().parent.parent / "aissy"


def _python_files():
    return [p for p in AISSY_DIR.rglob("*.py")]


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])

    return names


# Bibliotecas que observam ou controlam outros processos, teclado, mouse ou
# tela. São o tipo de coisa que a Riot proíbe e que o Vanguard monitora.
VANGUARD_SENSITIVE_LIBRARIES = {
    "pynput", "keyboard", "mouse", "pyautogui", "pydirectinput", "ctypes",
    "win32api", "win32gui", "win32process", "win32con", "pymem", "frida",
    "mss", "pyscreeze", "PIL", "cv2", "pygetwindow",
}

PROCESS_TOKENS = ("subprocess", "os.system", "os.popen", "Popen", "shutil")


def test_no_module_imports_input_hook_or_screen_libraries():
    for path in _python_files():
        found = _imports(path) & VANGUARD_SENSITIVE_LIBRARIES

        assert not found, f"{path.name} imports {found}"


def test_only_the_app_executor_starts_processes():
    for path in _python_files():
        text = path.read_text(encoding="utf-8")

        if path.name == "apps.py":
            continue

        assert "os.startfile" not in text, path.name

        for token in PROCESS_TOKENS:
            assert token not in text, f"{path.name} uses {token}"


def test_safety_package_has_no_dependency_on_tools_or_conversation():
    for path in (AISSY_DIR / "safety").glob("*.py"):
        text = path.read_text(encoding="utf-8")

        assert "aissy.tools" not in text and "aissy.conversation" not in text


# ---------- na conversa ----------

from aissy.apps import AppLauncher
from aissy.conversation import Conversation
from aissy.tasks import TaskStore


@pytest.fixture
def isolated(monkeypatch):
    class FakeMemory:
        def __init__(self, new_conversation=False):
            pass

        def load(self):
            return []

        def save(self, messages):
            pass

    class FakeLongTerm:
        def search_memories(self, query, limit=5):
            return []

    monkeypatch.setattr("aissy.conversation.Memory", FakeMemory)
    monkeypatch.setattr("aissy.conversation.LongTermMemory", FakeLongTerm)


class NoLLM:
    def generate(self, messages):
        raise AssertionError("o modelo não deveria ser chamado")


def test_reminder_is_blocked_when_the_layer_is_unavailable(isolated):
    store = TaskStore(":memory:")
    chat = Conversation("system", task_store=store, safety=None)

    answer = chat.send_message("me lembra de estudar amanhã", NoLLM())

    assert "Não posso fazer isso" in answer
    assert store.list_tasks() == []


def test_riot_game_cannot_be_opened_even_if_added_to_apps_json(isolated):
    opened = Counter()
    launcher = AppLauncher(
        apps={"valorant": "valorant.exe"},
        opener=lambda target: opened(),
    )
    layer = SafetyLayer(Policy(allowed_apps=launcher.names()), MemoryAuditLog())
    chat = Conversation("system", app_launcher=launcher, safety=layer)

    answer = chat.send_message("abre o valorant", NoLLM())

    assert "bloqueou" in answer
    assert opened.calls == 0


def test_blocked_tool_call_goes_back_to_the_model_as_an_error(isolated):
    store = TaskStore(":memory:")
    layer = SafetyLayer(Policy(), MemoryAuditLog())
    layer.halt()

    class LLM:
        def __init__(self):
            self.seen = []

        def generate_with_tools(self, messages, tools):
            self.seen.append([m.copy() for m in messages])

            if len(self.seen) == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "1",
                        "function": {
                            "name": "add_task",
                            "arguments": json.dumps({"title": "x"}),
                        },
                    }],
                }

            return {"role": "assistant", "content": "Não deu.", "tool_calls": []}

    llm = LLM()
    chat = Conversation("system", task_store=store, safety=layer)

    chat.send_message("preciso de ajuda com uma coisa importante", llm)

    tool_message = llm.seen[1][-1]

    assert tool_message["role"] == "tool"
    assert "Blocked by safety layer" in tool_message["content"]
    assert store.list_tasks() == []
