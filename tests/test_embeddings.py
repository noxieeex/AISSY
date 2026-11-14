# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

from unittest.mock import Mock, patch

import pytest
import requests

from aissy.embeddings import OllamaEmbedder
from aissy.errors import ProviderUnavailableError


@patch("aissy.embeddings.requests.post")
def test_embed_returns_vectors(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "embeddings": [[0.1, 0.2], [0.3, 0.4]]
    }
    mock_post.return_value = mock_response

    result = OllamaEmbedder().embed(["a", "b"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["input"] == ["a", "b"]


@patch("aissy.embeddings.requests.post")
def test_embed_raises_unavailable_when_connection_fails(mock_post):
    mock_post.side_effect = requests.exceptions.ConnectionError("refused")

    with pytest.raises(ProviderUnavailableError):
        OllamaEmbedder().embed(["a"])


def test_embed_rejects_empty_input():
    with pytest.raises(ValueError):
        OllamaEmbedder().embed([])


@patch("aissy.embeddings.requests.post")
def test_embed_raises_when_vector_count_does_not_match(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {"embeddings": [[0.1]]}
    mock_post.return_value = mock_response

    with pytest.raises(ValueError):
        OllamaEmbedder().embed(["a", "b"])