from aissy.conversation import Conversation
from aissy.providers.ollama_provider import OllamaProvider

SYSTEM_PROMPT = """
You are AISSY, a friendly personal assistant.

- Reply in the same language the user writes in.
- If the language is unclear (for example a short greeting like "oi"), reply in Brazilian Portuguese.
- Be natural, warm and concise.
- Ask a question when you need clarification.
"""

aissy = Conversation(SYSTEM_PROMPT)
llm = OllamaProvider()

print("AISSY iniciada! Digite 'exit' para encerrar.\n")

while True:
    user_input = input("You: ")

    if not user_input.strip():
        continue

    if user_input.lower() == "/new":
        aissy = Conversation(SYSTEM_PROMPT, new_conversation=True)
        print("\nAISSY: Nova conversa iniciada! <3\n")
        continue

    if user_input.lower() == "exit":
        print("AISSY: Até mais! <3")
        break

    try:
        response = aissy.send_message(user_input, llm)
        print(f"\nAISSY: {response}\n")

    except Exception as error:
        print(f"\nErro: {error}\n")