# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

from aissy.briefing import build_briefing


HELP_TEXT = (
    "Comandos:\n"
    "/hoje        resumo do dia\n"
    "/tarefas     lista as tarefas pendentes\n"
    "/feito N     marca a tarefa N como concluída\n"
    "/apagar N    apaga a tarefa N\n"
    "/parar       parada de emergência (bloqueia todas as ações)\n"
    "/retomar     libera as ações de novo\n"
    "/apps        mostra os apps que ela pode abrir\n"
    "/voz         volta ao modo voz (Ctrl+C para digitar)\n"
    "/texto       desliga a voz e fica só no texto\n"
    "/new         começa uma conversa nova\n"
    "tchau / exit encerra"
)


def _parse_id(argument):
    try:
        return int(argument)
    except (TypeError, ValueError):
        return None


def handle_command(text, task_store, now, name=None):
    """
    Trata comandos que começam com '/' sem passar pelo modelo.
    Devolve a resposta em texto, ou None se não for um comando daqui.
    """
    parts = text.strip().split(maxsplit=1)

    if not parts or not parts[0].startswith("/"):
        return None

    command = parts[0].lower()
    argument = parts[1].strip() if len(parts) > 1 else None

    if command == "/ajuda":
        return HELP_TEXT

    if command == "/hoje":
        return build_briefing(task_store, now, name=name)

    if command == "/tarefas":
        tasks = task_store.list_tasks()

        if not tasks:
            return "Nenhuma tarefa pendente. 💗"

        lines = []

        for task in tasks:
            due = f" — {task['due'].replace('T', ' ')}" if task["due"] else ""
            lines.append(f"#{task['id']} {task['title']}{due}")

        return "\n".join(lines)

    if command in ("/feito", "/apagar"):
        task_id = _parse_id(argument)

        if task_id is None:
            return f"Use assim: {command} N (N é o número da tarefa)."

        if command == "/feito":
            done = task_store.complete_task(task_id)
            return (
                f"Tarefa #{task_id} concluída!"
                if done
                else f"Não encontrei a tarefa pendente #{task_id}."
            )

        deleted = task_store.delete_task(task_id)
        return (
            f"Tarefa #{task_id} apagada."
            if deleted
            else f"Não encontrei a tarefa #{task_id}."
        )

    return None
