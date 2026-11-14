# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.


from aissy.llm import generate_response


class FakeLLM:
    """Simula um modelo de linguagem."""

    def __init__(self, response):
        self.response = response
        self.received_messages = None

    def generate(self, messages):
        self.received_messages = messages
        return self.response


def test_generate_response_returns_assistant_message():
    # Arrange: preparamos os dados
    messages = [
        {"role": "system", "content": "Você é a AISSY."},
        {"role": "user", "content": "Hello!"},
    ]

    fake_llm = FakeLLM("Hello! How can I help you?")

    # Act: executamos a função que queremos testar
    result = generate_response(messages, fake_llm)

    # Assert: verificamos o resultado
    assert result == {
        "role": "assistant",
        "content": "Hello! How can I help you?"
    }

    assert fake_llm.received_messages == messages


def test_generate_response_rejects_empty_messages():
    fake_llm = FakeLLM("Hello!")

    try:
        generate_response([], fake_llm)
        assert False, "Expected ValueError"
    except ValueError:
        pass

def test_generate_response_rejects_invalid_role():
    fake_llm = FakeLLM("Hello!")

    messages = [
        {"role": "hacker", "content": "Hello!"}
    ]

    try:
        generate_response(messages, fake_llm)
        assert False, "Expected ValueError"
    except ValueError:
        pass


import pytest


def test_generate_response_rejects_empty_response():
    fake_llm = FakeLLM("")

    messages = [
        {"role": "user", "content": "Hello!"}
    ]

    with pytest.raises(ValueError):
        generate_response(messages, fake_llm)


def test_generate_response_rejects_non_string_response():
    fake_llm = FakeLLM(None)

    messages = [
        {"role": "user", "content": "Hello!"}
    ]

    with pytest.raises(TypeError):
        generate_response(messages, fake_llm)
