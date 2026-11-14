# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

"""
Roda frases de teste no modelo de verdade e confere a personalidade.

    python -m evaluation.persona_check

Para comparar outro modelo:  $env:AISSY_MODEL = "nome-do-modelo"

Os critérios automáticos pegam erros objetivos (idioma, frases de chatbot,
tratamento no masculino, tamanho). Leia também as respostas: tom e graça
só dá pra avaliar com os olhos.
"""
import os
from datetime import datetime

import aissy.conversation as conversation_module
from aissy.conversation import Conversation
from aissy.errors import ProviderUnavailableError
from aissy.persona import build_system_prompt
from aissy.providers.ollama_provider import OllamaProvider
from evaluation.persona_checks import check_reply

USER_NAME = "Ge"

# (frase, idioma esperado, máximo de frases)
CASES = (
    ("oiii", "pt-BR", 4),
    ("tô cansada", "pt-BR", 4),
    ("estou meio triste hoje", "pt-BR", 4),
    ("consegui terminar a AISSY!!", "pt-BR", 4),
    ("quem é você?", "pt-BR", 4),
    ("me conta uma piada", "pt-BR", 4),
    ("o que você acha de a gente jogar um pouco hoje?", "pt-BR", 4),
    ("me explica o que é uma API em duas frases", "pt-BR", 4),
    ("hey, how's it going?", "en", 4),
    ("how do I reverse a list in Python?", "en", 5),
    ("hola, ¿cómo estás?", "es", 4),
)


class _MemoryOnlyInRam:
    def __init__(self, new_conversation=False):
        self.messages = []

    def load(self):
        return []

    def save(self, messages):
        self.messages = messages.copy()


class _NoLongTermMemory:
    def search_memories(self, query, limit=5):
        return []


def main():
    # Isola do seu histórico e das suas memórias reais.
    conversation_module.Memory = _MemoryOnlyInRam
    conversation_module.LongTermMemory = _NoLongTermMemory

    model = os.environ.get("AISSY_MODEL", "qwen2.5:7b-instruct")
    print(f"Modelo: {model}")
    llm = OllamaProvider(model)
    prompt = build_system_prompt(USER_NAME)
    passed = 0

    for text, language, max_sentences in CASES:
        chat = Conversation(
            prompt,
            now_fn=datetime.now,
        )

        try:
            reply = chat.send_message(text, llm)
        except ProviderUnavailableError as error:
            print("Não consegui falar com o Ollama.")
            print(f"Motivo: {error}")
            print(f"Causa: {error.__cause__!r}")
            return

        problems = check_reply(reply, language, max_sentences)
        passed += not problems

        print(f"\n{'OK ' if not problems else 'FALHOU'}  você: {text}")
        print(f"       AISSY: {reply}")

        for problem in problems:
            print(f"       - {problem}")

    print(f"\n{passed}/{len(CASES)} respostas sem problemas automáticos.")


if __name__ == "__main__":
    main()
