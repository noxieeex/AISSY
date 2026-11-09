import pytest
from unittest.mock import Mock, patch

from aissy.providers.ollama_provider import OllamaProvider


def test_provider_uses_qwen3_by_default():
    provider = OllamaProvider()
    assert provider.model == "qwen3:4b"


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

    mock_post.assert_called_once_with(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen3:4b",
            "messages": messages,
            "stream": False
        }
    )


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_raises_error_when_ollama_fails(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("Connection error")

    mock_post.return_value = mock_response

    provider = OllamaProvider()

    with pytest.raises(Exception, match="Connection error"):
        provider.generate([{"role": "user", "content": "Oi!"}])