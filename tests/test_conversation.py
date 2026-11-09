import pytest
from aissy.conversation import Conversation

@pytest.fixture(autouse=True)
def isolate_memory(monkeypatch):
    class TestMemory:
        def __init__(self, new_conversation=False):
            self.messages = []

        def load(self):
            return self.messages.copy()

        def save(self, messages):
            self.messages = messages.copy()

    monkeypatch.setattr(
        "aissy.conversation.Memory",
        TestMemory
    )

def test_conversation_starts_with_system_prompt():
    conversation = Conversation("You are AISSY.")

    assert conversation.get_messages() == [
        {
            "role": "system",
            "content": "You are AISSY."
        }
    ]


def test_conversation_stores_multiple_turns():
    conversation = Conversation("You are AISSY.")

    conversation.add_user_message("Hello!")
    conversation.add_assistant_message("Hello! How are you?")
    conversation.add_user_message("I am fine!")

    messages = conversation.get_messages()

    assert len(messages) == 4
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"


def test_conversation_preserves_message_order():
    conversation = Conversation("You are AISSY.")

    conversation.add_user_message("Hi")
    conversation.add_assistant_message("Hello")

    messages = conversation.get_messages()

    assert messages[1]["content"] == "Hi"
    assert messages[2]["content"] == "Hello"


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        return "Hello! Nice to meet you."


def test_send_message_integrates_conversation_and_llm():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message(
        "Hello!",
        fake_llm
    )

    assert response == "Hello! Nice to meet you."

    messages = conversation.get_messages()

    assert len(messages) == 3
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"

    assert len(fake_llm.calls) == 1


import pytest


def test_failed_llm_call_does_not_change_history():
    conversation = Conversation("You are AISSY.")

    class BrokenLLM:
        def generate(self, messages):
            raise RuntimeError("LLM unavailable")

    original_history = conversation.get_messages()

    with pytest.raises(RuntimeError):
        conversation.send_message(
            "Hello!",
            BrokenLLM()
        )

    assert conversation.get_messages() == original_history


def test_send_message_rejects_empty_content():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    with pytest.raises(ValueError):
        conversation.send_message("   ", fake_llm)
