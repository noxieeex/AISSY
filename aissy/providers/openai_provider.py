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

    def generate(self, messages):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        content = response.choices[0].message.content

        if content is None:
            raise ValueError("OpenAI returned an empty response.")

        return content