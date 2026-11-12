import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


DEFAULT_DB_PATH = Path("data") / "tasks.db"


def parse_due(value):
    """
    Valida um prazo e devolve texto ISO normalizado, ou None.
    Aceita 'YYYY-MM-DD' (dia inteiro) e 'YYYY-MM-DDTHH:MM' (com hora).
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("due must be a string.")

    text = value.strip()

    if not text:
        return None

    try:
        if len(text) == 10:
            return date.fromisoformat(text).isoformat()

        return datetime.fromisoformat(text).isoformat(timespec="minutes")
    except ValueError:
        raise ValueError(
            "due must look like YYYY-MM-DD or YYYY-MM-DDTHH:MM."
        ) from None


def _due_date(due):
    return date.fromisoformat(due[:10])


class TaskStore:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = str(db_path)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due TEXT,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        columns = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(tasks)")
        }

        # Bancos criados antes dos lembretes avisados ganham a coluna nova.
        if "notified" not in columns:
            self._connection.execute(
                "ALTER TABLE tasks ADD COLUMN notified INTEGER NOT NULL DEFAULT 0"
            )

        columns = [
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(tasks)")
        ]

        # Bancos criados antes dos avisos ganham a coluna nova.
        if "notified" not in columns:
            self._connection.execute(
                "ALTER TABLE tasks ADD COLUMN notified INTEGER NOT NULL DEFAULT 0"
            )

        self._connection.commit()

    @staticmethod
    def _to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "due": row["due"],
            "done": bool(row["done"]),
        }

    def add_task(self, title, due=None):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string.")

        due = parse_due(due)

        cursor = self._connection.execute(
            "INSERT INTO tasks (title, due, created_at) VALUES (?, ?, ?)",
            (title.strip(), due, datetime.now().isoformat(timespec="seconds")),
        )
        self._connection.commit()

        return self.get_task(cursor.lastrowid)

    def get_task(self, task_id):
        row = self._connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

        return self._to_dict(row) if row else None

    def list_tasks(self, include_done=False):
        query = "SELECT * FROM tasks"

        if not include_done:
            query += " WHERE done = 0"

        # Com prazo primeiro (mais cedo antes), depois sem prazo.
        query += " ORDER BY due IS NULL, due, id"

        rows = self._connection.execute(query).fetchall()

        return [self._to_dict(row) for row in rows]

    def complete_task(self, task_id):
        cursor = self._connection.execute(
            "UPDATE tasks SET done = 1, completed_at = ? "
            "WHERE id = ? AND done = 0",
            (datetime.now().isoformat(timespec="seconds"), task_id),
        )
        self._connection.commit()

        return cursor.rowcount > 0

    def delete_task(self, task_id):
        cursor = self._connection.execute(
            "DELETE FROM tasks WHERE id = ?", (task_id,)
        )
        self._connection.commit()

        return cursor.rowcount > 0

    def overdue_tasks(self, today):
        return [
            task for task in self.list_tasks()
            if task["due"] and _due_date(task["due"]) < today
        ]

    def tasks_due_on(self, day):
        return [
            task for task in self.list_tasks()
            if task["due"] and _due_date(task["due"]) == day
        ]

    def due_reminders(self, now):
        """Tarefas com hora marcada que já passou e ainda não avisaram."""
        limit = now.isoformat(timespec="minutes")

        rows = self._connection.execute(
            "SELECT * FROM tasks WHERE done = 0 AND notified = 0 "
            "AND due LIKE '%T%' AND due <= ? ORDER BY due, id",
            (limit,),
        ).fetchall()

        return [self._to_dict(row) for row in rows]

    def mark_notified(self, task_ids):
        for task_id in task_ids:
            self._connection.execute(
                "UPDATE tasks SET notified = 1 WHERE id = ?", (task_id,)
            )

        self._connection.commit()

    def due_reminders(self, now, grace_minutes=10):
        """
        Tarefas com horário que acabaram de vencer e ainda não foram avisadas.
        Vencidas há mais que a tolerância ficam só no resumo do dia.
        """
        rows = self._connection.execute(
            "SELECT * FROM tasks WHERE done = 0 AND notified = 0 "
            "AND due LIKE '%T%' ORDER BY due"
        ).fetchall()

        earliest = now - timedelta(minutes=grace_minutes)

        return [
            self._to_dict(row)
            for row in rows
            if earliest <= datetime.fromisoformat(row["due"]) <= now
        ]

    def mark_notified(self, task_id):
        self._connection.execute(
            "UPDATE tasks SET notified = 1 WHERE id = ?", (task_id,)
        )
        self._connection.commit()

    def close(self):
        self._connection.close()
