from datetime import datetime

from aissy.briefing import build_briefing
from aissy.commands import handle_command
from aissy.conversation import Conversation
from aissy.embeddings import OllamaEmbedder
from aissy.errors import ProviderUnavailableError
from aissy.long_term_memory import LongTermMemory
from aissy.providers.ollama_provider import OllamaProvider
from aissy.tasks import TaskStore


SYSTEM_PROMPT = """
You are AISSY, a warm, playful and capable personal assistant.

LANGUAGE:
- Always reply in the same language as the user's latest message.
- Brazilian Portuguese is the default language.
- Use English or Spanish when the user speaks them.
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

TASKS AND REMINDERS:
- When the user asks to be reminded of something or to add a to-do, call add_task. Never say a task was saved unless add_task succeeded.
- If a day is mentioned (tomorrow, Friday), call get_date first and pass the resulting date as due.
- When asked what is pending, call list_tasks and only report what it returns.
- To finish a task, call complete_task with its id (use list_tasks if you don't know it).
- If a tool returns an error, tell the user briefly and offer to try again.
"""


USER_NAME = None  # coloque seu nome aqui se quiser que a AISSY use na saudação

long_term_memory = LongTermMemory(embedder=OllamaEmbedder())
task_store = TaskStore()


def new_conversation(fresh=False):
    return Conversation(
        SYSTEM_PROMPT,
        new_conversation=fresh,
        long_term_memory=long_term_memory,
        task_store=task_store,
    )


aissy = new_conversation()
llm = OllamaProvider()

# Abertura proativa: a AISSY começa mostrando o dia, sem precisar de modelo.
print()
print(f"AISSY: {build_briefing(task_store, datetime.now(), USER_NAME)}")
print("\n(Digite /ajuda para ver os comandos.)\n")

while True:
    user_input = input("You: ")

    if not user_input.strip():
        continue

    if user_input.lower().strip() == "/new":
        aissy = new_conversation(fresh=True)
        print("\nAISSY: Nova conversa iniciada! <3\n")
        continue

    if user_input.lower().strip() == "exit":
        print("AISSY: Até mais! <3")
        break

    command_response = handle_command(
        user_input,
        task_store,
        datetime.now(),
        name=USER_NAME,
    )

    if command_response is not None:
        print(f"\nAISSY: {command_response}\n")
        continue

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
