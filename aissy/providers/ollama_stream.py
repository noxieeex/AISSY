# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import json
from uuid import uuid4

import requests

from aissy.errors import ProviderUnavailableError
from aissy.providers.ollama_provider import OllamaProvider


class OllamaStreamingProvider(OllamaProvider):
    """
    Igual ao OllamaProvider, mas entrega o texto aos poucos (streaming).
    O resto do comportamento (mensagens, modelo, URL) vem da classe base.
    """

    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 120  # tempo máximo esperando o próximo pedaço

    def generate_with_tools_stream(self, messages, tools, on_token):
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages),
            "stream": True,
            "options": {"num_predict": 512},
            "tools": tools,
        }

        parts = []
        tool_calls = []

        try:
            response = requests.post(
                self.url,
                json=payload,
                stream=True,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                chunk = json.loads(line)

                if "error" in chunk:
                    raise ProviderUnavailableError(
                        f"Ollama returned an error: {chunk['error']}"
                    )

                message = chunk.get("message") or {}
                text = message.get("content") or ""

                if text:
                    parts.append(text)
                    on_token(text)

                for call in message.get("tool_calls") or []:
                    function = call["function"]

                    tool_calls.append({
                        "id": uuid4().hex,
                        "type": "function",
                        "function": {
                            "name": function["name"],
                            "arguments": json.dumps(
                                function.get("arguments", {})
                            ),
                        },
                    })

                if chunk.get("done"):
                    break

        except requests.ConnectionError as error:
            raise ProviderUnavailableError(
                "Could not connect to Ollama."
            ) from error
        except requests.Timeout as error:
            raise ProviderUnavailableError(
                "Ollama took too long to respond."
            ) from error
        except requests.HTTPError as error:
            raise ProviderUnavailableError(
                f"Ollama returned an error: {error}"
            ) from error

        return {
            "role": "assistant",
            "content": "".join(parts) or None,
            "tool_calls": tool_calls,
        }
