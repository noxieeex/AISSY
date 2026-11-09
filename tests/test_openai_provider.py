
import pytest

from aissy.providers.openai_provider import OpenAIProvider


def test_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIProvider()
