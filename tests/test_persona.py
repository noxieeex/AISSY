# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import pytest

from aissy.conversation import Conversation
from aissy.persona import build_system_prompt
from evaluation.persona_checks import check_reply, count_sentences


@pytest.fixture(autouse=True)
def isolate_memory(monkeypatch):
    class FakeMemory:
        saved = []

        def __init__(self, new_conversation=False):
            pass

        def load(self):
            return FakeMemory.saved.copy()

        def save(self, messages):
            FakeMemory.saved = messages.copy()

    class FakeLongTerm:
        def search_memories(self, query, limit=5):
            return []

    FakeMemory.saved = []
    monkeypatch.setattr("aissy.conversation.Memory", FakeMemory)
    monkeypatch.setattr("aissy.conversation.LongTermMemory", FakeLongTerm)


class Recorder:
    def __init__(self):
        self.seen = []

    def generate(self, messages):
        self.seen.append([m.copy() for m in messages])
        return "Oii!"


# ---------- prompt ----------

def test_prompt_uses_the_name_and_feminine_identity():
    prompt = build_system_prompt("Ge")

    assert "Ge" in prompt
    assert "a AISSY" in prompt
    assert "feminine" in prompt


def test_prompt_works_without_a_name():
    assert "the user" in build_system_prompt(None)


def test_prompt_has_style_examples_marked_as_not_conversation():
    prompt = build_system_prompt("Ge")

    assert "STYLE EXAMPLES" in prompt
    assert "NOT part of the conversation" in prompt


def test_conversation_sends_only_system_and_user_messages():
    llm = Recorder()

    Conversation("system").send_message("oi, tudo bem?", llm)

    assert [m["role"] for m in llm.seen[0]] == ["system", "user"]


def test_old_saved_conversation_gets_the_current_system_prompt():
    first = Conversation("prompt antigo")
    first.send_message("oi, tudo bem?", Recorder())

    second = Conversation("prompt novo")

    assert second.get_messages()[0]["content"] == "prompt novo"
    assert len(second.get_messages()) == 3


# ---------- critérios automáticos ----------

def test_good_reply_has_no_problems():
    assert check_reply("Oii, Ge! Como foi o seu dia? 💗", "pt-BR") == []


@pytest.mark.parametrize(
    "reply",
    [
        "Oi! Como posso auxiliá-lo hoje?",
        "Fico feliz em ajudar você com tudo.",
        "Entendo como você se sente. Estou aqui para ouvir.",
        "Desenvolver o AISSY é emocionante!",
        "Um. Dois. Três. Quatro. Cinco. Seis.",
        "Oi 💗 tudo bem 😊?",
        "Oii! Eu sou a AISSY, seu assistente pessoal.",
        "Oii! Tô aqui pra ajudar se precisar de algo!",
        "",
    ],
)
def test_bad_replies_are_flagged(reply):
    assert check_reply(reply, "pt-BR")


def test_wrong_language_is_flagged():
    assert check_reply("Hey! How are you doing today?", "pt-BR")


def test_count_sentences():
    assert count_sentences("Oi! Tudo bem? Sim.") == 3


def test_emoji_is_not_counted_as_a_sentence():
    assert count_sentences("¡Hola! ¿Qué tal? 😊") == 2
