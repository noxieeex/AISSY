@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_raises_unavailable_error_on_timeout(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout("too slow")

    provider = OllamaProvider()

    with pytest.raises(ProviderUnavailableError):
        provider.generate([{"role": "user", "content": "Oi!"}])


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_raises_unavailable_error_on_http_error(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    mock_post.return_value = mock_response

    provider = OllamaProvider()

    with pytest.raises(ProviderUnavailableError):
        provider.generate([{"role": "user", "content": "Oi!"}])


@patch("aissy.providers.ollama_provider.requests.post")
def test_provider_sends_a_request_timeout(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {"message": {"content": "Oi"}}
    mock_post.return_value = mock_response

    OllamaProvider().generate([{"role": "user", "content": "Oi!"}])

    _, kwargs = mock_post.call_args
    assert kwargs["timeout"] > 0