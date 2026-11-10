
import pytest

from aissy.long_term_memory import LongTermMemory


@pytest.fixture
def memory(tmp_path):
    return LongTermMemory(tmp_path / "test_memory.db")


def test_add_memory(memory):
    memory_id = memory.add_memory("User studies Computer Engineering.")

    saved = memory.get_memory(memory_id)

    assert saved["content"] == "User studies Computer Engineering."
    assert saved["category"] == "general"
    assert saved["importance"] == 3


def test_memory_persists_after_reopening_database(tmp_path):
    path = tmp_path / "memory.db"

    first = LongTermMemory(path)
    memory_id = first.add_memory("User likes robotics.")

    second = LongTermMemory(path)

    assert second.get_memory(memory_id)["content"] == "User likes robotics."


def test_search_memories(memory):
    memory.add_memory(
        "User studies Computer Engineering.",
        category="studies",
    )
    memory.add_memory(
        "User enjoys playing games.",
        category="hobbies",
    )

    results = memory.search_memories("Computer Engineering")

    assert len(results) == 1
    assert results[0]["category"] == "studies"


def test_private_memory_is_not_returned_by_search(memory):
    memory.add_memory(
        "This is private information.",
        visibility="private",
    )

    assert memory.search_memories("private") == []


def test_private_memory_can_be_hidden_from_listing(memory):
    memory.add_memory("Public information.")
    memory.add_memory("Private information.", visibility="private")

    results = memory.list_memories(include_private=False)

    assert len(results) == 1
    assert results[0]["visibility"] == "normal"


def test_update_memory(memory):
    memory_id = memory.add_memory("User likes Python.")

    updated = memory.update_memory(
        memory_id,
        content="User enjoys Python development.",
        importance=5,
    )

    saved = memory.get_memory(memory_id)

    assert updated is True
    assert saved["content"] == "User enjoys Python development."
    assert saved["importance"] == 5


def test_delete_memory(memory):
    memory_id = memory.add_memory("Temporary information.")

    assert memory.delete_memory(memory_id) is True
    assert memory.get_memory(memory_id) is None


def test_add_memory_rejects_empty_content(memory):
    with pytest.raises(ValueError):
        memory.add_memory("   ")


def test_add_memory_rejects_invalid_importance(memory):
    with pytest.raises(ValueError):
        memory.add_memory("Some information.", importance=10)


def test_search_prioritizes_memories_with_more_matching_keywords(memory):
    memory.add_memory("User studies Computer Engineering.")
    memory.add_memory("User enjoys Computer Graphics.")

    results = memory.search_memories(
        "What do you know about my Computer Engineering studies?"
    )

    assert len(results) == 2
    assert "Engineering" in results[0]["content"]


def test_search_ignores_common_words(memory):
    memory.add_memory("User studies Computer Engineering.")

    results = memory.search_memories(
        "What do you know about my studies?"
    )

    assert len(results) == 1
    assert "Engineering" in results[0]["content"]


def test_search_returns_empty_when_no_keyword_matches(memory):
    memory.add_memory("User studies Computer Engineering.")

    results = memory.search_memories("favorite food")

    assert results == []


def test_search_rejects_invalid_limit(memory):
    with pytest.raises(ValueError):
        memory.search_memories("Computer", limit=0)


def test_search_does_not_return_private_memories_even_when_they_match(memory):
    memory.add_memory(
        "User studies Computer Engineering.",
        visibility="private",
    )

    results = memory.search_memories("Computer Engineering")

    assert results == []
