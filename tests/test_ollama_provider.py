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
    mock_post.side_effect