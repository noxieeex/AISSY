import requests


class OllamaProvider:
    def __init__(self, model="qwen2.5:7b-instruct"):
        self.model = model
        self.url = "http://localhost:11434/api/chat"

    def generate(self, messages):
        response = requests.post(
            self.url,
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": 512
                }
            }
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"]