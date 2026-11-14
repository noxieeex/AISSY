# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import requests

from aissy.errors import ProviderUnavailableError


class OllamaEmbedder:
    def __init__(
        self,
        model="bge-m3",
        url="http://localhost:11434/api/embed",
        timeout=60,
    ):
        self.model = model
        self.url = url
        self.timeout = timeout

    def embed(self, texts):
        if not isinstance(texts, list) or not texts:
            raise ValueError("Texts must be a non-empty list.")

        if not all(isinstance(text, str) and text.strip() for text in texts):
            raise ValueError("Every text must be a non-empty string.")

        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
        except (requests.ConnectionError, requests.Timeout) as error:
            raise ProviderUnavailableError(
                "Could not connect to Ollama for embeddings."
            ) from error

        response.raise_for_status()

        embeddings = response.json()["embeddings"]

        if len(embeddings) != len(texts):
            raise ValueError(
                "Ollama returned an unexpected number of embeddings."
            )

        return embeddings