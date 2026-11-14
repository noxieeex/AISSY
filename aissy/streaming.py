# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import re

BOUNDARY = re.compile(r"([.!?…]+[\"')\]]*)\s|\n")


class SentenceSplitter:
    """
    Junta os pedaços de texto que chegam do modelo em frases completas, para
    falar a primeira frase enquanto o resto ainda é gerado.

    - Frases muito curtas ("Oi!") são unidas à seguinte para a fala não ficar picada.
    - Blocos de código (```...```) só saem inteiros, depois de fechados.
    """

    def __init__(self, min_length=25):
        self.min_length = min_length
        self.buffer = ""
        self.pending = ""

    def _take_pending(self):
        sentence = self.pending.strip()
        self.pending = ""
        return sentence

    def feed(self, text):
        self.buffer += text
        sentences = []

        while True:
            # Dentro de um bloco de código aberto: espera fechar.
            if self.buffer.count("```") % 2 == 1:
                break

            match = BOUNDARY.search(self.buffer)

            if not match:
                break

            end = match.end(1) if match.group(1) else match.start()
            piece = self.buffer[:end]
            self.buffer = self.buffer[match.end():]

            self.pending = f"{self.pending} {piece}".strip()

            if len(self.pending) >= self.min_length:
                sentences.append(self._take_pending())

        return sentences

    def flush(self):
        """Devolve o que sobrou, no fim da resposta."""
        rest = f"{self.pending} {self.buffer}".strip()
        self.pending = ""
        self.buffer = ""

        return [rest] if rest else []
