"""
Adiciona a assinatura de autoria no topo dos arquivos .py do projeto.

Uso (na raiz do projeto, com o venv ativo):  python add_signature.py
Pode rodar mais de uma vez: não duplica. Ignora .venv, data e arquivos vazios.
Também troca "Ainda não definida." no README pelo aviso de direitos autorais.
"""

from pathlib import Path

SIGNATURE = (
    "# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).\n"
    "# Todos os direitos reservados.\n"
)
MARKER = "Geovana Ribeiro Borges"
SKIP = {".venv", "venv", "data", ".git", "__pycache__", ".pytest_cache"}

LICENSE_OLD = "Ainda não definida."
LICENSE_NEW = (
    "Copyright (c) 2026 Geovana Ribeiro Borges. Todos os direitos reservados. "
    "O código está público para leitura e avaliação; para reutilizá-lo, "
    "entre em contato."
)


def should_skip(path):
    return any(part in SKIP for part in path.parts)


def sign(path):
    text = path.read_text(encoding="utf-8")

    if not text.strip() or MARKER in text.split("\n\n", 1)[0]:
        return False

    lines = text.splitlines(keepends=True)
    keep = []

    # preserva #! e a linha de codificação, se existirem
    while lines and (lines[0].startswith("#!") or "coding" in lines[0][:20]):
        keep.append(lines.pop(0))

    path.write_text("".join(keep) + SIGNATURE + "\n" + "".join(lines), encoding="utf-8")
    return True


def main():
    changed = 0

    for path in sorted(Path(".").rglob("*.py")):
        if should_skip(path) or path.name == "add_signature.py":
            continue

        if sign(path):
            changed += 1
            print(f"assinado: {path}")

    readme = Path("README.md")

    if readme.exists():
        text = readme.read_text(encoding="utf-8")

        if LICENSE_OLD in text:
            readme.write_text(text.replace(LICENSE_OLD, LICENSE_NEW), encoding="utf-8")
            print("README: seção Licença atualizada")

    print(f"\n{changed} arquivo(s) assinado(s).")


if __name__ == "__main__":
    main()
