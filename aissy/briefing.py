from aissy.tools import WEEKDAYS_PT


def _greeting(hour):
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"


def _format_task(task):
    due = task["due"]

    if due and "T" in due:
        return f"#{task['id']} {task['title']} (às {due[11:16]})"

    return f"#{task['id']} {task['title']}"


def build_briefing(task_store, now, name=None):
    """
    Resumo do dia em português, montado em código (sem depender do modelo):
    saudação, data, tarefas atrasadas, de hoje e sem prazo.
    """
    today = now.date()
    weekday = WEEKDAYS_PT[today.weekday()]
    greeting = _greeting(now.hour)

    if name:
        greeting += f", {name}"

    lines = [f"{greeting}! Hoje é {weekday}, {today.strftime('%d/%m/%Y')}."]

    overdue = task_store.overdue_tasks(today)
    due_today = task_store.tasks_due_on(today)
    no_due = [t for t in task_store.list_tasks() if not t["due"]]

    if not (overdue or due_today or no_due):
        lines.append("Você não tem tarefas pendentes. Dia livre! 💗")
        return "\n".join(lines)

    if overdue:
        lines.append("\nAtrasadas:")
        lines.extend(f"- {_format_task(t)}" for t in overdue)

    if due_today:
        lines.append("\nPara hoje:")
        lines.extend(f"- {_format_task(t)}" for t in due_today)

    if no_due:
        lines.append("\nSem prazo:")
        lines.extend(f"- {_format_task(t)}" for t in no_due)

    return "\n".join(lines)
