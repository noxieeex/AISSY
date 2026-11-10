import re

from aissy.errors import ProviderUnavailableError
from aissy.long_term_memory import LongTermMemory


class FakeEmbedder:
    """Cada conceito vira um eixo; palavras do mesmo conceito se aproximam."""

    model = "fake"

    concepts = (
        {"studies", "study", "engineering", "computer", "ufu",
         "university", "curso", "universidade", "faculdade", "estuda"},
        {"games", "game", "playing", "jogo", "jogos", "jogar"},
        {"pizza", "food", "comida", "comer"},
        {"drawing", "art", "desenhar", "arte"},
    )

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def _vector(self, text):
        words = re.findall(r"[a-zA-ZÀ-ÿ0-9_]+", text.lower())
        vector = [
            float(sum(word in concept for word in words))
            for concept in self.concepts
        ]
        vector.append(0.01)
        return vector


class BrokenEmbedder:
    model = "broken"

    def embed(self, texts):
        raise ProviderUnavailableError("down")


def make_memory(tmp_path, embedder=None):
    return LongTermMemory(tmp_path / "memory.db", embedder=embedder)


def test_retrieval_finds_memory_by_meaning_without_shared_words(tmp_path):
    memory = make_memory(tmp_path, FakeEmbedder())
    memory.add_memory(
        "User studies Computer Engineering at UFU.",
        category="studies",
    )

    query = "Qual é o meu curso na universidade?"

    assert memory.search_memories(query) == []

    results = memory.retrieve_memories(query)

    assert len(results) == 1
    assert results[0]["category"] == "studies"


def test_retrieval_ignores_unrelated_memories(tmp_path):
    memory = make_memory(tmp_path, FakeEmbedder())
    memory.add_memory("User enjoys playing games.", category="hobbies")

    assert memory.retrieve_memories("What is my favorite food?") == []


def test_private_memory_is_never_embedded_or_retrieved(tmp_path):
    embedder = FakeEmbedder()
    memory = make_memory(tmp_path, embedder)
    memory.add_memory(
        "User studies Computer Engineering at UFU.",
        visibility="private",
    )

    results = memory.retrieve_memories("Qual é o meu curso na universidade?")

    embedded_texts = [text for call in embedder.calls for text in call]

    assert results == []
    assert "User studies Computer Engineering at UFU." not in embedded_texts


def test_retrieval_falls_back_to_lexical_when_embedder_fails(tmp_path):
    memory = make_memory(tmp_path, BrokenEmbedder())
    memory.add_memory("User studies Computer Engineering.")

    results = memory.retrieve_memories("Computer Engineering")

    assert len(results) == 1


def test_retrieval_without_embedder_behaves_like_lexical_search(tmp_path):
    memory = make_memory(tmp_path)
    memory.add_memory("User studies Computer Engineering.")

    assert memory.retrieve_memories("Computer Engineering") == (
        memory.search_memories("Computer Engineering")
    )


def test_updating_content_refreshes_the_embedding(tmp_path):
    memory = make_memory(tmp_path, FakeEmbedder())
    memory_id = memory.add_memory("User enjoys playing games.")

    assert len(memory.retrieve_memories("jogos")) == 1

    memory.update_memory(
        memory_id,
        content="User studies Computer Engineering at UFU.",
    )

    assert memory.retrieve_memories("jogos") == []
    assert len(memory.retrieve_memories("faculdade")) == 1


def test_deleted_memory_is_not_retrieved(tmp_path):
    memory = make_memory(tmp_path, FakeEmbedder())
    memory_id = memory.add_memory("User enjoys playing games.")

    assert len(memory.retrieve_memories("jogos")) == 1

    memory.delete_memory(memory_id)

    assert memory.retrieve_memories("jogos") == []


def test_retrieval_respects_limit(tmp_path):
    memory = make_memory(tmp_path, FakeEmbedder())
    memory.add_memory("User studies Computer Engineering.")
    memory.add_memory("User studies mathematics at UFU.")
    memory.add_memory("User likes university life.")

    assert len(memory.retrieve_memories("faculdade", limit=2)) == 2


def test_embeddings_are_reused_between_queries(tmp_path):
    embedder = FakeEmbedder()
    memory = make_memory(tmp_path, embedder)
    memory.add_memory("User enjoys playing games.")

    memory.retrieve_memories("jogos")
    memory.retrieve_memories("jogar")

    # 1 chamada para indexar a memória + 1 por consulta
    assert len(embedder.calls) == 3


def test_memory_matching_both_searches_ranks_first(tmp_path):
    memory = make_memory(tmp_path, FakeEmbedder())
    best_id = memory.add_memory("User studies Computer Engineering at UFU.")
    memory.add_memory("User likes university life.")

    results = memory.retrieve_memories("Computer Engineering studies")

    assert results[0]["id"] == best_id