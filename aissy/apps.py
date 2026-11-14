# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import json
import os
import re
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("data") / "apps.json"

# Apps que a AISSY pode abrir. Só o que está aqui (ou em data/apps.json)
# pode ser aberto: a permissão fica no código, não no prompt.
DEFAULT_APPS = {
    "bloco de notas": "notepad.exe",
    "calculadora": "calc.exe",
    "explorador de arquivos": "explorer.exe",
    "chrome": "chrome",
    "spotify": "spotify:",
}

ALIASES = {
    "notepad": "bloco de notas",
    "calculator": "calculadora",
    "google chrome": "chrome",
    "navegador": "chrome",
    "explorer": "explorador de arquivos",
}


def _normalize(name):
    name = re.sub(r"^(?:o|a|os|as|the)\s+", "", name.strip().lower())
    name = re.sub(r"^(?:app|aplicativo|programa)\s+(?:do|da|de)?\s*", "", name)
    return name.strip(" .!?")


def _default_opener(target):
    if not hasattr(os, "startfile"):
        raise RuntimeError("Abrir aplicativos só funciona no Windows.")

    os.startfile(target)


class AppLauncher:
    def __init__(self, apps=None, opener=None, config_path=DEFAULT_CONFIG_PATH):
        self.apps = dict(DEFAULT_APPS if apps is None else apps)
        self.opener = opener or _default_opener

        if apps is None:
            self._load_user_apps(Path(config_path))

    def _load_user_apps(self, path):
        """Apps extras do usuário: {"nome": "caminho ou comando"}."""
        if not path.exists():
            return

        try:
            extra = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return

        if isinstance(extra, dict):
            for name, target in extra.items():
                if isinstance(name, str) and isinstance(target, str):
                    self.apps[name.lower()] = target

    def names(self):
        return sorted(self.apps)

    def find(self, name):
        """Nome do app permitido que corresponde ao texto, ou None."""
        if not isinstance(name, str):
            return None

        key = _normalize(name)
        key = ALIASES.get(key, key)

        return key if key in self.apps else None

    def open(self, name):
        key = self.find(name)

        if key is None:
            raise ValueError(
                f"App not allowed or unknown: {name!r}. "
                f"Available: {', '.join(self.names())}."
            )

        self.opener(self.apps[key])

        return key
