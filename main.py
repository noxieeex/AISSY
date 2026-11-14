# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import os
import sys
from datetime import datetime

from aissy.apps import AppLauncher
from aissy.briefing import build_briefing
from aissy.commands import handle_command
from aissy.conversation import Conversation, detect_language
from aissy.embeddings import OllamaEmbedder
from aissy.errors import ProviderUnavailableError
from aissy.long_term_memory import LongTermMemory
from aissy.persona import build_system_prompt
from aissy.providers.ollama_stream import OllamaStreamingProvider
from aissy.reminders import collect_due_reminders
from aissy.safety import FileAuditLog, Policy, SafetyLayer, is_stop_phrase
from aissy.tasks import TaskStore
from aissy.voice import is_exit_phrase


USER_NAME = "Ge"  # como a AISSY te chama

SYSTEM_PROMPT = build_system_prompt(USER_NAME)

long_term_memory = LongTermMemory(embedder=OllamaEmbedder())
task_store = TaskStore()
app_launcher = AppLauncher()

# Safety Layer: todas as ações com efeito passam por ela. Se a verificação
# inicial falhar, nenhuma ação é executada (fail closed).
safety = SafetyLayer(
    Policy(allowed_apps=app_launcher.names()),
    FileAuditLog(),
)

if not safety.self_check():
    print(
        "\n[SEGURANÇA] A verificação da Safety Layer falhou. "
        "Nenhuma ação (tarefas, abrir apps) será executada nesta sessão.\n"
    )
    safety = None
voice = None
listening_notice_shown = False

# Voz neural (online, opcional): --voz-online ou AISSY_TTS=edge
ONLINE_VOICE = "--voz-online" in sys.argv or os.environ.get("AISSY_TTS") == "edge"


def new_conversation(fresh=False):
    return Conversation(
        SYSTEM_PROMPT,
        new_conversation=fresh,
        long_term_memory=long_term_memory,
        task_store=task_store,
        app_launcher=app_launcher,
        safety=safety,
    )


def emit(text):
    """Mostra a fala da AISSY e, no modo voz, também fala em voz alta."""
    print(f"\nAISSY: {text}\n")

    if voice is not None:
        try:
            voice.say(text, detect_language(text))
        except KeyboardInterrupt:
            print("(fala interrompida)\n")
        except Exception as error:
            print(f"(não consegui falar em voz alta: {error})\n")


def reply_with_stream(user_input):
    """Mostra (e fala) a resposta frase a frase, enquanto ela é gerada."""
    state = {"started": False, "muted": False}

    def on_sentence(sentence):
        print("\nAISSY: " if not state["started"] else " ", end="", flush=True)
        state["started"] = True
        print(sentence, end="", flush=True)

        if voice is not None and not state["muted"]:
            try:
                voice.say(sentence, aissy.last_language)
            except KeyboardInterrupt:
                state["muted"] = True
                print(" (fala interrompida)", end="", flush=True)
            except Exception as error:
                state["muted"] = True
                print(f" (não consegui falar em voz alta: {error})", end="", flush=True)

    text = aissy.send_message(user_input, llm, on_sentence=on_sentence)

    if aissy.streamed:
        if state["started"]:
            print("\n")
    else:
        emit(text)


def turn_voice_on(announce=True):
    global voice

    try:
        from aissy.voice import create_voice_session

        voice = create_voice_session(online=ONLINE_VOICE)
    except ImportError:
        voice = None
        print(
            "\nAISSY: Faltam as bibliotecas de voz, então vou ficar no texto. "
            "Para usar voz, rode: pip install -r requirements-voice.txt "
            "(e requirements-voice-online.txt para a voz neural)\n"
        )
        return

    if announce:
        emit("Modo voz ligado! Pode falar, eu tô ouvindo.")


def read_input():
    """Voz: ouve sozinha (Ctrl+C para digitar). Texto: input normal."""
    if voice is None:
        return input("You: ")

    global listening_notice_shown

    if not listening_notice_shown:
        print("🎙️  Ouvindo... (Ctrl+C para digitar)")
        listening_notice_shown = True

    try:
        text = voice.listen(auto=True)
    except KeyboardInterrupt:
        listening_notice_shown = False
        return input("You (digitando, Enter volta a ouvir): ")
    except Exception as error:
        print(f"\nAISSY: Problema com o microfone ou o modelo de voz: {error}")
        print("Voltei pro modo texto. Digite /voz para tentar de novo.\n")
        turn_voice_off()
        return ""

    if text:
        listening_notice_shown = False
        print(f"You (voz): {text}")

    return text


def turn_voice_off():
    global voice
    voice = None


aissy = new_conversation()
MODEL = os.environ.get("AISSY_MODEL", "qwen2.5:7b-instruct")
llm = OllamaStreamingProvider(MODEL)

print(f"\n(Modelo: {MODEL})")

# Voz é o modo principal. Use --texto para começar só no texto.
if "--texto" not in sys.argv:
    turn_voice_on(announce=False)

emit(build_briefing(task_store, datetime.now(), USER_NAME))
print("(Digite /ajuda para ver os comandos. Diga \"tchau\" para sair.)\n")

while True:
    # Avisa lembretes que venceram (a cada ciclo; no modo voz, a cada poucos segundos).
    for reminder in collect_due_reminders(task_store, datetime.now(), USER_NAME):
        emit(reminder)

    try:
        user_input = read_input()
    except (EOFError, KeyboardInterrupt):
        print("\nAISSY: Até mais! <3")
        break

    if not user_input.strip():
        continue

    try:
        command = user_input.lower().strip()

        if command == "/new":
            aissy = new_conversation(fresh=True)
            emit("Nova conversa iniciada! <3")
            continue

        if command == "/parar" or is_stop_phrase(user_input):
            if safety is not None:
                safety.halt()

            emit(
                "Parada de emergência ativada. Não vou executar nenhuma ação "
                "até você dizer /retomar."
            )
            continue

        if command == "/retomar":
            if safety is not None:
                safety.resume()

            emit("Ok, ações liberadas de novo.")
            continue

        if command == "/apps":
            emit("Posso abrir: " + ", ".join(app_launcher.names()) + ".")
            continue

        if command == "/texto":
            turn_voice_off()
            print("\nAISSY: Modo texto. Digite /voz para voltar a conversar por voz.\n")
            continue

        if command == "/voz":
            if voice is None:
                turn_voice_on()
            else:
                print("\nAISSY: Já estou no modo voz. Use /texto para sair dele.\n")
            continue

        if command == "exit" or is_exit_phrase(user_input):
            emit("Até mais! <3")
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
            reply_with_stream(user_input)

        except ProviderUnavailableError as error:
            emit(
                "Não consegui falar com o Ollama. Veja o erro na tela."
            )
            print(f"Detalhe: {error}")
            print(
                f"Modelo em uso: {MODEL}. Confira se o Ollama está aberto "
                "e se esse modelo existe e aceita ferramentas.\n"
            )

        except Exception as error:
            print(f"\nErro inesperado: {error}\n")

    except KeyboardInterrupt:
        print("\n(interrompido)\n")
