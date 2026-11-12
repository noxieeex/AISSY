import json
from pathlib import Path

DEFAULT_AUDIT_PATH = Path("data") / "audit.log"
MAX_VALUE_LENGTH = 200


class AuditError(Exception):
    """Não foi possível registrar no log de auditoria."""


def summarize_args(args):
    """Resumo curto dos argumentos para o log."""
    return {
        str(key): str(value)[:MAX_VALUE_LENGTH]
        for key, value in args.items()
    }


class FileAuditLog:
    """Log JSONL só de acréscimo. A API não tem como editar nem apagar."""

    def __init__(self, path=DEFAULT_AUDIT_PATH):
        self.path = Path(path)

    def record(self, entry):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.path, "a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except (OSError, TypeError, ValueError) as error:
            raise AuditError(str(error)) from error


class MemoryAuditLog:
    """Versão em memória, para testes."""

    def __init__(self):
        self.entries = []

    def record(self, entry):
        self.entries.append(dict(entry))
