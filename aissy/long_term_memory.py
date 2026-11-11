import json
import logging
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MIN_SIMILARITY = 0.5  # chute inicial; a avaliação calibra
RRF_K = 60
CANDIDATE_POOL = 20


class LongTermMemory:
    def __init__(self, db_path="data/long_term_memory.db", embedder=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder
        self._initialize_database()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row

        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _initialize_database(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    importance INTEGER NOT NULL DEFAULT 3,
                    visibility TEXT NOT NULL DEFAULT 'normal',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    memory_id INTEGER PRIMARY KEY,
                    model TEXT NOT NULL,
                    vector TEXT NOT NULL
                )
            """)

    def add_memory(
        self,
        content,
        category="general",
        importance=3,
        visibility="normal",
    ):
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Memory content cannot be empty.")

        if not isinstance(category, str) or not category.strip():
            raise ValueError("Memory category cannot be empty.")

        if (
            not isinstance(importance, int)
            or isinstance(importance, bool)
            or not 1 <= importance <= 5
        ):
            raise ValueError("Importance must be an integer from 1 to 5.")

        if visibility not in ("normal", "private"):
            raise ValueError("Visibility must be 'normal' or 'private'.")

        now = self._now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories (
                    content, category, importance,
                    visibility, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    content.strip(),
                    category.strip(),
                    importance,
                    visibility,
                    now,
                    now,
                ),
            )

            return cursor.lastrowid

    def get_memory(self, memory_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()

        return dict(row) if row else None

    def list_memories(self, include_private=True):
        query = "SELECT * FROM memories"
        parameters = ()

        if not include_private:
            query += " WHERE visibility = ?"
            parameters = ("normal",)

        query += " ORDER BY importance DESC, updated_at DESC"

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [dict(row) for row in rows]

    def search_memories(self, query, limit=5):
        if not isinstance(query, str) or not query.strip():
            return []

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError("Limit must be a positive integer.")

        stop_words = {
            "the", "is", "are", "am", "you", "your", "what",
            "how", "can", "could", "would", "please", "do",
            "does", "did", "about", "my", "me", "i", "it",
            "a", "an", "and", "or", "to", "of", "in", "on",
            "for", "with", "this", "that",
            "o", "a", "os", "as", "um", "uma", "de", "do",
            "da", "dos", "das", "e", "ou", "para", "por",
            "com", "em", "no", "na", "nos", "nas", "meu",
            "minha", "meus", "minhas", "sobre", "eu", "voce",
            "voces", "que", "qual", "quais",
        }

        keywords = re.findall(
            r"[a-zA-ZÀ-ÿ0-9_]+",
            query.lower(),
        )

        keywords = list(dict.fromkeys(
            word for word in keywords
            if word not in stop_words
        ))

        if not keywords:
            return []

        conditions = []
        score_conditions = []
        search_parameters = []

        for keyword in keywords:
            pattern = f"%{keyword}%"

            conditions.append(
                "(content LIKE ? OR category LIKE ?)"
            )
            search_parameters.extend([pattern, pattern])

            score_conditions.append(
                "(CASE WHEN content LIKE ? OR category LIKE ? "
                "THEN 1 ELSE 0 END)"
            )

        score_sql = " + ".join(score_conditions)
        conditions_sql = " OR ".join(conditions)

        sql = f"""
            SELECT *,
                ({score_sql}) AS relevance
            FROM memories
            WHERE visibility = 'normal'
            AND ({conditions_sql})
            ORDER BY relevance DESC, importance DESC, updated_at DESC
            LIMIT ?
        """

        parameters = (
            search_parameters.copy()
            + search_parameters
            + [limit]
        )

        with self._connect() as connection:
            rows = connection.execute(
                sql,
                parameters,
            ).fetchall()

        return [dict(row) for row in rows]

    def index_missing(self):
        """Gera embeddings das memórias normais que ainda não têm."""
        if self.embedder is None:
            return 0

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT m.id, m.content
                FROM memories m
                LEFT JOIN memory_embeddings e
                    ON e.memory_id = m.id AND e.model = ?
                WHERE m.visibility = 'normal'
                AND e.memory_id IS NULL
                """,
                (self.embedder.model,),
            ).fetchall()

        if not rows:
            return 0

        vectors = self.embedder.embed([row["content"] for row in rows])

        with self._connect() as connection:
            for row, vector in zip(rows, vectors):
                connection.execute(
                    """
                    INSERT OR REPLACE INTO memory_embeddings
                        (memory_id, model, vector)
                    VALUES (?, ?, ?)
                    """,
                    (row["id"], self.embedder.model, json.dumps(vector)),
                )

        return len(rows)

    @staticmethod
    def _cosine(first, second):
        dot = sum(a * b for a, b in zip(first, second))
        first_norm = math.sqrt(sum(a * a for a in first))
        second_norm = math.sqrt(sum(b * b for b in second))

        if first_norm == 0 or second_norm == 0:
            return 0.0

        return dot / (first_norm * second_norm)

    def semantic_search(
        self,
        query,
        limit=5,
        min_similarity=DEFAULT_MIN_SIMILARITY,
    ):
        if (
            self.embedder is None
            or not isinstance(query, str)
            or not query.strip()
        ):
            return []

        self.index_missing()

        query_vector = self.embedder.embed([query.strip()])[0]

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT m.*, e.vector
                FROM memories m
                JOIN memory_embeddings e ON e.memory_id = m.id
                WHERE m.visibility = 'normal' AND e.model = ?
                """,
                (self.embedder.model,),
            ).fetchall()

        scored = []

        for row in rows:
            item = dict(row)
            vector = json.loads(item.pop("vector"))
            similarity = self._cosine(query_vector, vector)

            if similarity >= min_similarity:
                item["similarity"] = similarity
                scored.append(item)

        scored.sort(key=lambda item: item["similarity"], reverse=True)

        return scored[:limit]

    @staticmethod
    def _reciprocal_rank_fusion(rankings):
        scores = {}
        items = {}

        for ranking in rankings:
            for position, item in enumerate(ranking, start=1):
                scores[item["id"]] = (
                    scores.get(item["id"], 0) + 1 / (RRF_K + position)
                )
                items.setdefault(item["id"], item)

        ordered = sorted(
            items.values(),
            key=lambda item: item["updated_at"],
            reverse=True,
        )
        ordered.sort(key=lambda item: item["importance"], reverse=True)
        ordered.sort(key=lambda item: scores[item["id"]], reverse=True)

        return ordered

    def retrieve_memories(
        self,
        query,
        limit=5,
        min_similarity=DEFAULT_MIN_SIMILARITY,
    ):
        """Busca híbrida: palavras-chave + significado, fundidas por RRF."""
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError("Limit must be a positive integer.")

        lexical = self.search_memories(query, limit=CANDIDATE_POOL)

        if self.embedder is None:
            return lexical[:limit]

        try:
            semantic = self.semantic_search(
                query,
                limit=CANDIDATE_POOL,
                min_similarity=min_similarity,
            )
        except Exception as error:
            logger.warning(
                "Semantic search unavailable, using lexical only: %s",
                error,
            )
            return lexical[:limit]

        return self._reciprocal_rank_fusion([lexical, semantic])[:limit]

    def update_memory(self, memory_id, **updates):
        allowed_fields = {
            "content",
            "category",
            "importance",
            "visibility",
        }

        if not updates:
            return False

        if not set(updates).issubset(allowed_fields):
            raise ValueError("Invalid memory field.")

        if "content" in updates:
            if (
                not isinstance(updates["content"], str)
                or not updates["content"].strip()
            ):
                raise ValueError("Memory content cannot be empty.")

            updates["content"] = updates["content"].strip()

        if "category" in updates:
            if (
                not isinstance(updates["category"], str)
                or not updates["category"].strip()
            ):
                raise ValueError("Memory category cannot be empty.")

            updates["category"] = updates["category"].strip()

        if "importance" in updates:
            value = updates["importance"]

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 1 <= value <= 5
            ):
                raise ValueError("Importance must be an integer from 1 to 5.")

        if "visibility" in updates:
            if updates["visibility"] not in ("normal", "private"):
                raise ValueError("Invalid visibility.")

        invalidates_embedding = (
            "content" in updates or "visibility" in updates
        )

        updates["updated_at"] = self._now()

        assignments = ", ".join(
            f"{field} = ?" for field in updates
        )

        values = list(updates.values())
        values.append(memory_id)

        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE memories SET {assignments} WHERE id = ?",
                values,
            )

            if invalidates_embedding:
                connection.execute(
                    "DELETE FROM memory_embeddings WHERE memory_id = ?",
                    (memory_id,),
                )

        return cursor.rowcount > 0

    def delete_memory(self, memory_id):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM memory_embeddings WHERE memory_id = ?",
                (memory_id,),
            )
            cursor = connection.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,),
            )

        return cursor.rowcount > 0