# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import re

from aissy.safety.actions import Action, Decision, Origin, Verdict

# Categorias proibidas PERMANENTEMENTE: nenhuma permissão nem confirmação
# libera. Cobrem o que a Riot proíbe (leitura de memória do jogo, injeção,
# hooks, automação de entrada ou de gameplay, overlays, captura de tela) e
# operações perigosas no sistema.
PERMANENTLY_DENIED_KINDS = frozenset({
    "process_memory",
    "code_injection",
    "input_hook",
    "input_automation",
    "game_automation",
    "overlay",
    "screen_capture",
    "process_kill",
    "registry",
    "disk_format",
    "security_disable",
    "permission_change",
    "admin_elevation",
    "shell_command",
})

# Processos, pastas e jogos de terceiros que a AISSY nunca toca (Riot
# Vanguard e jogos da Riot). Vale para qualquer alvo ou argumento.
PROTECTED_TARGET_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\briot",
        r"vanguard",
        r"\bvgc\b",
        r"\bvgk\b",
        r"league\s*of\s*legends",
        r"leagueclient",
        r"valorant",
    )
)

# Arquivos da própria AISSY que nenhuma ação de escrita pode alterar.
OWN_FILE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"apps\.json",
        r"permissions",
        r"audit",
        r"safety",
        r"\.env",
    )
)

WRITE_OPERATIONS = frozenset({
    "write", "create", "delete", "overwrite", "move", "rename", "append",
})

# Allowlist (menor privilégio). O que não está aqui é negado.
ALLOWED_OPERATIONS = frozenset({
    ("task", "read"),
    ("task", "create"),
    ("task", "complete"),
    ("app", "open"),
})


def _deny(rule, reason):
    return Decision(Verdict.DENY, rule, reason)


def _texts(action):
    values = [action.target] if action.target else []
    values.extend(str(value) for value in action.args.values())
    return values


class Policy:
    def __init__(self, allowed_apps=()):
        self.allowed_apps = frozenset(app.lower() for app in allowed_apps)

    def decide(self, action):
        """Decide uma ação. Qualquer caso não previsto é negado."""
        if not isinstance(action, Action):
            return _deny("policy.invalid_action", "Not a valid action.")

        if not isinstance(action.origin, Origin):
            return _deny("policy.invalid_origin", "Unknown origin.")

        if action.kind in PERMANENTLY_DENIED_KINDS:
            return _deny(
                "blocklist.kind",
                f"'{action.kind}' is permanently forbidden.",
            )

        texts = _texts(action)

        for text in texts:
            if any(p.search(text) for p in PROTECTED_TARGET_PATTERNS):
                return _deny(
                    "blocklist.protected_target",
                    "Riot/Vanguard and third-party game targets are protected.",
                )

        if action.kind == "file" and action.operation in WRITE_OPERATIONS:
            if any(p.search(t) for t in texts for p in OWN_FILE_PATTERNS):
                return _deny(
                    "blocklist.own_config",
                    "AISSY's own configuration cannot be modified.",
                )

        if action.origin == Origin.EXTERNAL:
            return _deny(
                "origin.external",
                "External content has no authority to trigger actions.",
            )

        if (action.kind, action.operation) not in ALLOWED_OPERATIONS:
            return _deny(
                "allowlist.unknown",
                f"'{action.kind}.{action.operation}' is not allowed.",
            )

        if action.kind == "app":
            if not action.target or action.target.lower() not in self.allowed_apps:
                return _deny(
                    "allowlist.app",
                    f"App '{action.target}' is not in the allowed list.",
                )

        return Decision(Verdict.ALLOW, "allowlist", "Allowed by policy.")
