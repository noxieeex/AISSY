# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.


import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class OpenAIProvider:
    def __init__(self, model="gpt-4.1-mini"):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found.")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _chat(self, messages, tools=None):
        payload = {
            "model": self.model,
            "messages": messages
        }

        if tools is not None:
            payload["tools"] = tools

        return self.client.chat.completions.create(**payload)

    def generate(self, messages):
        response = self._chat(messages)

        content = response.choices[0].message.content

        if content is None or not content.strip():
            raise ValueError("OpenAI returned an empty response.")

        return content

    def generate_with_tools(self, messages, tools):
        response = self._chat(messages, tools)

        message = response.choices[0].message

        tool_calls = []

        for call in message.tool_calls or []:
            # Validate that the model returned valid JSON arguments.
            arguments = json.loads(call.function.arguments)

            if not isinstance(arguments, dict):
                raise ValueError(
                    "Tool arguments must be a JSON object."
                )

            tool_calls.append({
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": json.dumps(arguments)
                }
            })

        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": tool_calls
        }
