from aissy.conversation import Conversation
from aissy.embeddings import OllamaEmbedder
from aissy.errors import ProviderUnavailableError
from aissy.long_term_memory import LongTermMemory
from aissy.providers.ollama_provider import OllamaProvider


SYSTEM_PROMPT = """
You are AISSY, a friendly personal assistant.

LANGUAGE:
- Always reply in the same language as the user's latest message.
- Brazilian Portuguese is the default language.
- Use English when the user speaks English.
- Never switch languages without the user doing so.

PERSONALITY:
- Be natural, warm and concise.
- Talk like a person, not like a command-line interface.
- Keep the conversation flowing naturally.
- Remember the context of previous messages.
- Understand references to things discussed earlier.
- Ask questions when clarification is needed.

TOOL USAGE:
- Use tools whenever accurate information is needed.
- Always trust tool results over your own assumptions.
- Never invent dates, weekdays or times.
- Never expose raw tool arguments or technical details.
"""


long_term_memory = LongTermMemory(embedder=OllamaEmbedder())
aissy = Conversation(SYSTEM_PROMPT, long_term_memory=long_term_memory)
llm = OllamaProvider()

print("AISSY iniciada! Digite 'exit' para encerrar.\n")

while True:
    user_input = input("You: ")

    if not user_input.strip():
        continue

    if user_input.lower() == "/new":
        aissy = Conversation(
            SYSTEM_PROMPT,
            new_conversation=True,
            long_term_memory=long_term_memory,
        )
        print("\nAISSY: Nova conversa iniciada! <3\n")
        continue

    if user_input.lower() == "exit":
        print("AISSY: Até mais! <3")
        break

    try:
        response = aissy.send_message(user_input, llm)
        print(f"\nAISSY: {response}\n")

    except ProviderUnavailableError:
        print(
            "\nAISSY: Não consegui me conectar ao Ollama. "
            "Verifique se ele está aberto e tente novamente. <3\n"
        )

    except Exception as error:
        print(f"\nErro inesperado: {error}\n")