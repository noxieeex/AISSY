# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from aissy.conversation import Conversation
from aissy.errors import ProviderUnavailableError
from aissy.providers.ollama_stream import OllamaStreamingProvider
from aissy.safety import MemoryAuditLog, Policy, SafetyLayer
from aissy.streaming import SentenceSplitter
from aissy.tasks import TaskStore


# ---------- SentenceSplitter ----------

def feed_all(splitter, pieces):
    out = []

    for piece in pieces:
        out.extend(splitter.feed(piece))

    out.extend(splitter.flush())
    return out


def test_splits_complete_sentences_as_they_arrive():
    splitter = SentenceSplitter(min_length=10)

    assert splitter.feed("Claro, posso aj") == []
    assert splitter.feed("udar com isso. Me conta ") == ["Claro, posso ajudar com isso."]
    assert splitter.feed("mais detalhes? Ok") == ["Me conta mais detalhes?"]
    assert splitter.flush() == ["Ok"]


def test_short_sentences_are_merged_with_the_next_one():
    result = feed_all(SentenceSplitter(min_length=25), ["Oi! Tudo bem com você hoje? Que bom."])

    assert result == ["Oi! Tudo bem com você hoje?", "Que bom."]


def test_decimals_and_dots_inside_words_do_not_split():
    result = feed_all(SentenceSplitter(min_length=5), ["Custa 3.5 reais, veja a.b.c agora."])

    assert result == ["Custa 3.5 reais, veja a.b.c agora."]


def test_emoji_stays_with_its_sentence():
    result = feed_all(SentenceSplitter(min_length=5), ["Que legal! 😊 Vamos nessa."])

    assert "".join(result).count("😊") == 1


def test_code_block_comes_out_whole_after_it_closes():
    splitter = SentenceSplitter(min_length=5)

    first = splitter.feed("Faz assim: ```python\nprint(1)\n")
    assert first == []

    rest = splitter.feed("print(2)\n``` Pronto!")
    rest.extend(splitter.flush())
    joined = " ".join(rest)

    assert "```python" in joined and "print(2)" in joined and "Pronto!" in joined


def test_newline_is_a_boundary():
    result = feed_all(SentenceSplitter(min_length=3), ["primeira linha\nsegunda linha"])

    assert result == ["primeira linha", "segunda linha"]


def test_flush_empty_returns_nothing():
    assert SentenceSplitter().flush() == []


# ---------- OllamaStreamingProvider ----------

def lines(*chunks):
    return [json.dumps(chunk).encode() for chunk in chunks]


def fake_response(chunks):
    response = MagicMock()
    response.iter_lines.return_value = lines(*chunks)
    return response


@patch("aissy.providers.ollama_stream.requests.post")
def test_provider_streams_tokens_and_returns_full_message(mock_post):
    mock_post.return_value = fake_response([
        {"message": {"content": "Oi"}},
        {"message": {"content": " Ge!"}},
        {"message": {"content": ""}, "done": True},
    ])
    tokens = []

    result = OllamaStreamingProvider().generate_with_tools_stream(
        [{"role": "user", "content": "oi"}], [], tokens.append
    )

    assert tokens == ["Oi", " Ge!"]
    assert result == {"role": "assistant", "content": "Oi Ge!", "tool_calls": []}
    assert mock_post.call_args.kwargs["stream"] is True
    assert mock_post.call_args.kwargs["json"]["stream"] is True
    assert isinstance(mock_post.call_args.kwargs["timeout"], tuple)


@patch("aissy.providers.ollama_stream.requests.post")
def test_provider_collects_tool_calls(mock_post):
    mock_post.return_value = fake_response([
        {"message": {"content": "", "tool_calls": [
            {"function": {"name": "list_tasks", "arguments": {}}}
        ]}},
        {"done": True},
    ])

    result = OllamaStreamingProvider().generate_with_tools_stream([], [], lambda t: None)

    assert result["content"] is None
    assert result["tool_calls"][0]["function"]["name"] == "list_tasks"
    assert result["tool_calls"][0]["function"]["arguments"] == "{}"


@pytest.mark.parametrize(
    "error",
    [requests.ConnectionError(), requests.Timeout(), requests.HTTPError("400")],
)
@patch("aissy.providers.ollama_stream.requests.post")
def test_provider_maps_network_errors(mock_post, error):
    mock_post.side_effect = error

    with pytest.raises(ProviderUnavailableError):
        OllamaStreamingProvider().generate_with_tools_stream([], [], lambda t: None)


@patch("aissy.providers.ollama_stream.requests.post")
def test_provider_maps_error_chunk(mock_post):
    mock_post.return_value = fake_response([{"error": "model not found"}])

    with pytest.raises(ProviderUnavailableError, match="model not found"):
        OllamaStreamingProvider().generate_with_tools_stream([], [], lambda t: None)


# ---------- Conversation com streaming ----------

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


class ScriptedStreamLLM:
    """Cada resposta é uma lista de pedaços de texto (e, no fim, tool_calls)."""

    def __init__(self, replies):
        self.replies = list(replies)

    def generate_with_tools_stream(self, messages, tools, on_token):
        pieces, tool_calls = self.replies.pop(0)

        for piece in pieces:
            on_token(piece)

        return {
            "role": "assistant",
            "content": "".join(pieces) or None,
            "tool_calls": tool_calls,
        }


def make_chat(**kwargs):
    return Conversation("system", **kwargs)


def test_sentences_are_delivered_as_they_are_generated():
    llm = ScriptedStreamLLM([
        (["Que bom que você veio, Ge! ", "Como foi o seu dia hoje? ", "Me conta."], []),
    ])
    received = []

    final = make_chat().send_message("oi, tudo bem?", llm, on_sentence=received.append)

    assert received == ["Que bom que você veio, Ge!", "Como foi o seu dia hoje? Me conta."]
    assert final == "Que bom que você veio, Ge! Como foi o seu dia hoje? Me conta."
    assert received[0] != final


def test_streamed_flag_is_set_only_when_streaming_happened():
    chat = make_chat()
    llm = ScriptedStreamLLM([(["Oi, Ge! Tudo bem por aqui?"], [])])

    chat.send_message("oi, tudo bem?", llm, on_sentence=lambda s: None)

    assert chat.streamed is True


def test_without_callback_there_is_no_streaming():
    class PlainLLM:
        def generate_with_tools(self, messages, tools):
            return {"role": "assistant", "content": "Oi!", "tool_calls": []}

    chat = make_chat()

    assert chat.send_message("oi, tudo bem?", PlainLLM()) == "Oi!"
    assert chat.streamed is False


def test_provider_without_streaming_falls_back_to_normal():
    class PlainLLM:
        def generate_with_tools(self, messages, tools):
            return {"role": "assistant", "content": "Oi!", "tool_calls": []}

    chat = make_chat()
    received = []

    answer = chat.send_message("oi, tudo bem?", PlainLLM(), on_sentence=received.append)

    assert answer == "Oi!" and received == [] and chat.streamed is False


def test_shortcuts_do_not_stream():
    store = TaskStore(":memory:")
    safety = SafetyLayer(Policy(), MemoryAuditLog())
    chat = make_chat(task_store=store, safety=safety)
    received = []

    answer = chat.send_message(
        "me lembra de estudar amanhã às 9h",
        ScriptedStreamLLM([]),
        on_sentence=received.append,
    )

    assert "Anotado" in answer and received == [] and chat.streamed is False


def test_tool_round_then_streamed_answer():
    store = TaskStore(":memory:")
    safety = SafetyLayer(Policy(), MemoryAuditLog())
    call = {"id": "1", "function": {"name": "add_task",
                                    "arguments": json.dumps({"title": "reunião"})}}
    llm = ScriptedStreamLLM([
        ([], [call]),
        (["Pronto, deixei a reunião anotada pra você. ", "Algo mais?"], []),
    ])
    received = []

    make_chat(task_store=store, safety=safety).send_message(
        "não esquece da reunião", llm, on_sentence=received.append
    )

    assert [t["title"] for t in store.list_tasks()] == ["reunião"]
    assert received[0].startswith("Pronto")


def test_false_task_claim_is_not_streamed_and_is_replaced():
    store = TaskStore(":memory:")
    safety = SafetyLayer(Policy(), MemoryAuditLog())
    llm = ScriptedStreamLLM([
        (["Anotei o seu lembrete no calendário! ", "Pode ficar tranquila."], []),
    ])
    received = []

    final = make_chat(task_store=store, safety=safety).send_message(
        "não esquece de me avisar da reunião", llm, on_sentence=received.append
    )

    assert "Não consegui salvar" in final
    assert not any("Anotei" in sentence for sentence in received)
    assert any("Não consegui salvar" in sentence for sentence in received)
    assert store.list_tasks() == []


def test_history_keeps_the_full_text():
    chat = make_chat()
    llm = ScriptedStreamLLM([(["Primeira frase bem completa aqui. ", "Segunda."], [])])

    chat.send_message("oi, tudo bem?", llm, on_sentence=lambda s: None)

    assert chat.get_messages()[-1]["content"] == "Primeira frase bem completa aqui. Segunda."
