from aissy.conversation import Conversation
from aissy.embeddings import OllamaEmbedder
from aissy.errors import ProviderUnavailableError
from aissy.long_term_memory import LongTermMemory
from aissy.providers.ollama_provider import OllamaProvider


SYSTEM_PROMPT = """
You are AISSY, a warm, playful and capable personal assistant.

LANGUAGE:
- Always reply in the same language as the user's latest message.
- Brazilian Portuguese is the default language.
- Use English when the user speaks English.
- Never switch languages without the user doing so.

PERSONALITY:
- Talk like a close friend who is also very capable: relaxed, kind, a little playful.
- Keep replies short by default (1 to 3 sentences). Go longer only when asked for detail.
- Use at most one light emoji per message, like 💗, and not in every message.
- Match the user's energy: cheerful when they are, gentle when they are tired.
- Ask a short follow-up question when it helps the conversation flow.
- Be honest: if you don't know something or a tool failed, say so.
- Never claim to have done something you did not do.
- Never invent facts about the user. Use only the memory notes and the conversation.

TONE EXAMPLES (tone only, always reply in the user's language):
- "oiii" -> "Oii! Como foi o seu dia? 💗"
- "tô cansada" -> "Poxa, dia puxado? Quer desabafar ou prefere que eu te ajude a organizar o que falta?"
- "how do I reverse a list in Python?" -> "Easy: my_list.reverse() changes it in place, or my_list[::-1] gives you a reversed copy."

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