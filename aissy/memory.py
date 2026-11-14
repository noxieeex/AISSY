# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import json
from pathlib import Path
from uuid import uuid4


class Memory:
    def __init__(self, new_conversation=False):
        self.directory = Path("data/conversations")
        self.directory.mkdir(parents=True, exist_ok=True)

        self.session_file = Path("data/last_conversation.txt")

        if new_conversation:
            self.conversation_id = str(uuid4())

        elif self.session_file.exists():
            self.conversation_id = self.session_file.read_text(
                encoding="utf-8"
            ).strip()

        else:
            self.conversation_id = str(uuid4())

        if not self.conversation_id:
            self.conversation_id = str(uuid4())

        self.session_file.write_text(
            self.conversation_id,
            encoding="utf-8"
        )

        self.file_path = self.directory / f"{self.conversation_id}.json"

    def load(self):
        if not self.file_path.exists():
            return []

        with open(self.file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def save(self, messages):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(messages, file, ensure_ascii=False, indent=4)