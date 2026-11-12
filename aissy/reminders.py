def collect_due_reminders(task_store, now, name=None):
    """
    Devolve as frases dos lembretes que venceram agora e marca cada um como
    avisado, para não repetir. Chamada a cada ciclo do laço principal.
    """
    messages = []

    for task in task_store.due_reminders(now):
        task_store.mark_notified(task["id"])

        if name:
            messages.append(f"{name}, lembrete: {task['title']}!")
        else:
            messages.append(f"Lembrete: {task['title']}!")

    return messages
