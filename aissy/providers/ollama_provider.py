# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import json
from uuid import uuid4

import requests

from aissy.errors import ProviderUnavailableError


class OllamaProvider:
    def __init__(self, model="qwen2.5:7b-instruct", timeout=120):
        self.model = model
        self.timeout = timeout
        self.url = "http://localhost:11434/api/chat"

    def _prepare_messages(self, messages):
        prepared_messages = []

        for message in messages:
            if message["role"] == "assistant" and message.get("tool_calls"):
                tool_calls = []

                for call in message["tool_calls"]:
                    arguments = call["function"]["arguments"]

                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)

                    tool_calls.append({
                        "function": {
                            "name": call["function"]["name"],
                            "arguments": arguments
                        }
                    })

                prepared_messages.append({
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": tool_calls
                })

            elif message["role"] == "tool":
                prepared_messages.append({
                    "role": "tool",
                    "tool_name": message["name"],
                    "content": message["content"]
                })

            else:
                prepared_messages.append(message.copy())

        return prepared_messages

    def _chat(self, messages, tools=None):
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages),
            "stream": False,
            "options": {
                "num_predict": 512
            }
        }

        if tools is not None:
            payload["tools"] = tools

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout,
            )
        except (requests.ConnectionError, requests.Timeout) as error:
            raise ProviderUnavailableError(
                "Could not reach Ollama (connection failed or timed out)."
            ) from error

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise ProviderUnavailableError(
                f"Ollama returned an error: {error}"
            ) from error

        return response.json()["message"]

    def generate(self, messages):
        message = self._chat(messages)

        return message["content"]

    def generate_with_tools(self, messages, tools):
        message = self._chat(messages, tools)

        tool_calls = []

        for call in message.get("tool_calls", []):
            function = call["function"]

            tool_calls.append({
                "id": uuid4().hex,
                "type": "function",
                "function": {
                    "name": function["name"],
                    "arguments": json.dumps(
                        function.get("arguments", {})
                    )
                }
            })

        return {
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": tool_calls
        }