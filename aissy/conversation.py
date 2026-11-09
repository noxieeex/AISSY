from aissy.llm import generate_response
from aissy.memory import Memory


class Conversation:
    def __init__(self, system_prompt, new_conversation=False):
        self.memory = Memory(new_conversation=new_conversation)

        saved_messages = self.memory.load()

        if saved_messages:
            self.messages = saved_messages
        else:
            self.messages = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]

        self.memory.save(self.messages)

    def add_user_message(self, content):
        self.messages.append({
            "role": "user",
            "content": content
        })

    def add_assistant_message(self, content):
        self.messages.append({
            "role": "assistant",
            "content": content
        })

    def get_messages(self):
        return self.messages.copy()

    def send_message(self, content, llm):
        if not isinstance(content, str):
            raise TypeError("Message content must be a string.")

        if not content.strip():
            raise ValueError("Message content cannot be empty.")

        messages = self.get_messages()

        messages.append({
            "role": "user",
            "content": content
        })

        response = generate_response(messages, llm)

        self.add_user_message(content)
        self.add_assistant_message(response["content"])

        self.memory.save(self.messages)

        return response["content"]