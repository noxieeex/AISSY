
import json
import pytest
import requests
from unittest.mock import Mock, patch

from aissy.errors import ProviderUnavailableError
from aissy.providers.ollama_provider import OllamaProvider


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_sends_messages_to_ollama(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "message": {
            "content": "Olá! Eu sou a AISSY."
        }
    }

    mock_post.return_value = mock_response

    provider = OllamaProvider()

    messages = [
        {"role": "user", "content": "Oi!"}
    ]

    result = provider.generate(messages)

    assert result == "Olá! Eu sou a AISSY."

    args, kwargs = mock_post.call_args
    assert args[0] == "http://localhost:11434/api/chat"
    assert kwargs["json"]["messages"] == messages
    assert kwargs["json"]["stream"] is False


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_returns_only_content_when_model_sends_thinking(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "message": {
            "content": "Olá!",
            "thinking": "O usuário disse oi, vou responder."
        }
    }

    mock_post.return_value = mock_response

    provider = OllamaProvider()

    result = provider.generate([{"role": "user", "content": "Oi!"}])

    assert result == "Olá!"


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_raises_error_when_ollama_fails(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("Connection error")

    mock_post.return_value = mock_response

    provider = OllamaProvider()

    with pytest.raises(Exception, match="Connection error"):
        provider.generate([{"role": "user", "content": "Oi!"}])


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_raises_unavailable_error_when_connection_fails(mock_post):
    error = requests.ConnectionError("Connection refused")
    mock_post.side_effect = error

    provider = OllamaProvider()

    with pytest.raises(ProviderUnavailableError) as exc_info:
        provider.generate([{"role": "user", "content": "Oi!"}])

    assert exc_info.value.__cause__ is error


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_sends_tools_and_returns_tool_calls(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_current_datetime",
                        "arguments": {}
                    }
                }
            ]
        }
    }

    mock_post.return_value = mock_response

    provider = OllamaProvider()

    messages = [
        {"role": "user", "content": "Que horas são?"}
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "Get current date and time",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]

    result = provider.generate_with_tools(messages, tools)

    sent_payload = mock_post.call_args.kwargs["json"]

    assert sent_payload["tools"] == tools
    assert result["role"] == "assistant"
    assert result["content"] == ""
    assert len(result["tool_calls"]) == 1

    call = result["tool_calls"][0]

    assert call["type"] == "function"
    assert call["function"]["name"] == "get_current_datetime"
    assert json.loads(call["function"]["arguments"]) == {}


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_converts_tool_history_to_ollama_format(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "message": {
            "content": "São 18 horas."
        }
    }

    mock_post.return_value = mock_response

    provider = OllamaProvider()

    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call123",
                    "type": "function",
                    "function": {
                        "name": "get_current_datetime",
                        "arguments": "{}"
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "call123",
            "name": "get_current_datetime",
            "content": "Monday, 2026-11-09, 18:00"
        }
    ]

    provider.generate_with_tools(messages, [])

    sent_messages = mock_post.call_args.kwargs["json"]["messages"]

    assert sent_messages[0]["tool_calls"][0]["function"]["name"] == (
        "get_current_datetime"
    )
    assert sent_messages[0]["tool_calls"][0]["function"]["arguments"] == {}

    assert sent_messages[1] == {
        "role": "tool",
        "tool_name": "get_current_datetime",
        "content": "Monday, 2026-11-09, 18:00"
    }
