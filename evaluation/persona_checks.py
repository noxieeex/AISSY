# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import re

from aissy.conversation import detect_language

BANNED_PHRASES = (
    r"como posso (?:te )?ajudar",
    r"como posso auxili",
    r"fico feliz em ajudar",
    r"estou aqui para (?:te )?ouvir",
    r"entendo como você se sente",
    r"se precisar de algo",
    r"aqui pra ajudar",
    r"how can i (?:help|assist)",
    r"i'?m here to help",
)

MASCULINE_ADDRESS = r"\b\w+á-lo\b|\bo senhor\b|\bseu assistente\b"
SELF_AS_PROJECT = r"\bo aissy\b"
EMOJI = "[\U0001F000-\U0001FAFF☀-➿]"


def count_sentences(text):
    text = re.sub(EMOJI, "", text)
    parts = re.split(r"[.!?…]+\s*", text.strip())
    return len([p for p in parts if re.search(r"\w", p)])


def check_reply(reply, expected_language, max_sentences=4):
    """Devolve a lista de problemas encontrados na resposta (vazia = ok)."""
    problems = []
    lowered = reply.lower()

    if not reply.strip():
        return ["resposta vazia"]

    if detect_language(reply) != expected_language:
        problems.append(f"idioma diferente do esperado ({expected_language})")

    for pattern in BANNED_PHRASES:
        if re.search(pattern, lowered):
            problems.append(f"frase de chatbot genérico: /{pattern}/")

    if re.search(MASCULINE_ADDRESS, lowered):
        problems.append("usou forma masculina (para a Ge ou para si mesma)")

    if re.search(SELF_AS_PROJECT, lowered):
        problems.append('chamou a si mesma de "o AISSY"')

    if count_sentences(reply) > max_sentences:
        problems.append(f"mais de {max_sentences} frases")

    if len(re.findall(EMOJI, reply)) > 1:
        problems.append("mais de um emoji")

    return problems
