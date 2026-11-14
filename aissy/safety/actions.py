# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

from dataclasses import dataclass, field
from enum import Enum


class Origin(str, Enum):
    """De onde veio o pedido. Define o nível de confiança."""

    USER = "user"          # a própria usuária (comando ou fala dela)
    MODEL = "model"        # proposta do modelo de IA
    EXTERNAL = "external"  # conteúdo externo (arquivo, página): sem autoridade


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


@dataclass(frozen=True)
class Action:
    """Algo que a AISSY quer fazer num recurso fora do próprio raciocínio."""

    kind: str
    operation: str
    origin: Origin
    target: str | None = None
    args: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    rule: str
    reason: str

    @property
    def allowed(self):
        return self.verdict == Verdict.ALLOW
