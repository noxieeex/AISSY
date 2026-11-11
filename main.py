import os
import sys
from datetime import datetime

from aissy.briefing import build_briefing
from aissy.commands import handle_command
from aissy.conversation import Conversation, detect_language
from aissy.embeddings import OllamaEmbedder
from aissy.errors import ProviderUnavailableError
from aissy.long_term_memory import LongTermMemory
from aissy.persona import build_system_prompt
from aissy.providers.ollama_provider import OllamaProvider
from aissy.tasks import TaskStore


USER_NAME = "Ge"  # como a AISSY te chama

SYSTEM_PROMPT = build_system_prompt(USER_NAME)

long_term_memory = LongTermMemory(embedder=OllamaEmbedder())
task_store = TaskStore()
voice = None


def new_conversation(fresh=False):
    return Conversation(
        SYSTEM_PROMPT,
        new_conversation=fresh,
        long_term_memory=long_term_memory,
        task_store=task_store,
    )


def emit(text):
    """Mostra a fala da AISSY e, no modo voz, também fala em voz alta."""
    print(f"\nAISSY: {text}\n")

    if voice is not None:
        try:
            voice.say(text, detect_language(text))
        except Exception as error:
            print(f"(não consegui falar em voz alta: {error})\n")


def turn_voice_on():
    global voice

    try:
        from aissy.voice import create_voice_session

        voice = create_voice_session()
    except ImportError:
        print(
            "\nAISSY: Faltam as bibliotecas de voz. Rode:\n"
            "pip install -r requirements-voice.txt\n"
        )
        return

    emit(
        "Modo voz ligado! Aperte Enter sem digitar nada para falar, "
        "ou escreva normalmente."
    )


aissy = new_conversation()
llm = OllamaProvider(os.environ.get("AISSY_MODEL", "qwen2.5:7b-instruct"))

print()
if "--voz" in sys.argv:
    turn_voice_on()

emit(build_briefing(task_store, datetime.now(), USER_NAME))
print("(Digite /ajuda para ver os comandos.)\n")

while True:
    user_input = input("You: ")

    if not user_input.strip():
        if voice is None:
            continue

        try:
            user_input = voice.listen()
        except Exception as error:
            print(f"\nAISSY: Erro com o microfone ou o modelo de voz: {error}\n")
            continue

        if not user_input:
            print("\nAISSY: Não consegui ouvir nada. Tenta de novo? <3\n")
            continue

        print(f"You (voz): {user_input}")

    command = user_input.lower().strip()

    if command == "/new":
        aissy = new_conversation(fresh=True)
        emit("Nova conversa iniciada! <3")
        continue

    if command == "/voz":
        if voice is None:
            turn_voice_on()
        else:
            voice = None
            print("\nAISSY: Modo voz desligado.\n")
        continue

    if command == "exit":
        print("AISSY: Até mais! <3")
        break

    command_response = handle_command(
        user_input,
        task_store,
        datetime.now(),
        name=USER_NAME,
    )

    if command_response is not None:
        emit(command_response)
        continue

    try:
        emit(aissy.send_message(user_input, llm))

    except ProviderUnavailableError:
        emit(
            "Não consegui me conectar ao Ollama. "
            "Verifique se ele está aberto e tente novamente. <3"
        )

    except Exception as error:
        print(f"\nErro inesperado: {error}\n")
