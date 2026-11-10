
import pytest

from aissy.conversation import Conversation, detect_language


@pytest.fixture(autouse=True)
def isolate_memory(monkeypatch):
    import re

    class TestMemory:
        def __init__(self, new_conversation=False):
            self.messages = []

        def load(self):
            return self.messages.copy()

        def save(self, messages):
            self.messages = messages.copy()

    class TestLongTermMemory:
        def __init__(self):
            self.memories = []
            self.next_id = 1

        def search_memories(self, query, limit=5):
            stop_words = {
                "the", "is", "are", "am", "you", "your",
                "what", "how", "can", "could", "would",
                "please", "do", "does", "did", "about",
                "my", "me", "i", "it", "a", "an", "and",
                "or", "to", "of", "in", "on", "for", "with",
                "this", "that", "o", "os", "as", "um",
                "uma", "de", "do", "da", "dos", "das", "e",
                "ou", "para", "por", "com", "em", "no", "na",
                "nos", "nas", "meu", "minha", "sobre", "eu",
                "que", "qual", "quais",
            }

            keywords = re.findall(
                r"[a-zA-ZÀ-ÿ0-9_]+",
                query.lower(),
            )

            keywords = [
                word for word in keywords
                if word not in stop_words
            ]

            results = []

            for item in self.memories:
                if item.get("visibility", "normal") != "normal":
                    continue

                searchable_text = (
                    item["content"] + " " + item.get("category", "")
                ).lower()

                if any(
                    keyword in searchable_text
                    for keyword in keywords
                ):
                    results.append(item)

            return results[:limit]

        def add_memory(
            self,
            content,
            category="general",
            importance=3,
            visibility="normal",
        ):
            memory_id = self.next_id
            self.next_id += 1

            self.memories.append({
                "id": memory_id,
                "content": content,
                "category": category,
                "importance": importance,
                "visibility": visibility,
            })

            return memory_id

        def delete_memory(self, memory_id):
            for item in self.memories:
                if item["id"] == memory_id:
                    self.memories.remove(item)
                    return True

            return False

    monkeypatch.setattr(
        "aissy.conversation.Memory",
        TestMemory,
    )

    monkeypatch.setattr(
        "aissy.conversation.LongTermMemory",
        TestLongTermMemory,
    )


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        return "Hello! Nice to meet you."


def test_conversation_starts_with_system_prompt():
    conversation = Conversation("You are AISSY.")

    assert conversation.get_messages() == [
        {
            "role": "system",
            "content": "You are AISSY.",
        }
    ]


def test_conversation_stores_multiple_turns():
    conversation = Conversation("You are AISSY.")

    conversation.add_user_message("Hello!")
    conversation.add_assistant_message("Hello! How are you?")
    conversation.add_user_message("I am fine!")

    messages = conversation.get_messages()

    assert len(messages) == 4
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"


def test_conversation_preserves_message_order():
    conversation = Conversation("You are AISSY.")

    conversation.add_user_message("Hi")
    conversation.add_assistant_message("Hello")

    messages = conversation.get_messages()

    assert messages[1]["content"] == "Hi"
    assert messages[2]["content"] == "Hello"


def test_send_message_integrates_conversation_and_llm():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message("Hello!", fake_llm)

    assert response == "Hello! Nice to meet you."

    messages = conversation.get_messages()

    assert len(messages) == 3
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert len(fake_llm.calls) == 1


def test_failed_llm_call_does_not_change_history():
    conversation = Conversation("You are AISSY.")

    class BrokenLLM:
        def generate(self, messages):
            raise RuntimeError("LLM unavailable")

    original_history = conversation.get_messages()

    with pytest.raises(RuntimeError):
        conversation.send_message("Hello!", BrokenLLM())

    assert conversation.get_messages() == original_history


def test_send_message_rejects_empty_content():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    with pytest.raises(ValueError):
        conversation.send_message("   ", fake_llm)


def test_detects_brazilian_portuguese():
    assert detect_language(
        "Estou desenvolvendo um projeto chamado AISSY."
    ) == "pt-BR"


def test_detects_english():
    assert detect_language(
        "I am developing a project called AISSY."
    ) == "en"


def test_detects_simple_english_greeting():
    assert detect_language("Hello!") == "en"


def test_detects_simple_portuguese_greeting():
    assert detect_language("Oi!") == "pt-BR"


def test_defaults_to_portuguese_when_uncertain():
    assert detect_language("AISSY") == "pt-BR"


def test_portuguese_instruction_is_added_to_model_context():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.send_message(
        "Estou desenvolvendo um projeto chamado AISSY.",
        fake_llm,
    )

    system_message = fake_llm.calls[0][0]

    assert "português brasileiro" in system_message["content"]


def test_english_instruction_is_added_to_model_context():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.send_message(
        "I am developing a project called AISSY.",
        fake_llm,
    )

    system_message = fake_llm.calls[0][0]

    assert "Reply entirely in English" in system_message["content"]


def test_language_instruction_does_not_change_saved_system_prompt():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.send_message("Hello!", fake_llm)

    assert conversation.get_messages()[0]["content"] == "You are AISSY."


def test_relevant_memory_is_added_to_model_context():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.long_term_memory.memories = [
        {
            "id": 1,
            "content": "User studies Computer Engineering.",
            "category": "studies",
            "visibility": "normal",
        }
    ]

    conversation.send_message(
        "Tell me about my studies.",
        fake_llm,
    )

    system_message = fake_llm.calls[0][0]

    assert "User studies Computer Engineering." in system_message["content"]


def test_private_memory_is_never_added_to_model_context():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.long_term_memory.memories = [
        {
            "id": 1,
            "content": "Private information.",
            "category": "personal",
            "visibility": "private",
        }
    ]

    conversation.send_message(
        "Tell me something about myself.",
        fake_llm,
    )

    system_message = fake_llm.calls[0][0]

    assert "Private information." not in system_message["content"]


def test_conversation_works_without_relevant_memories():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message("Hello!", fake_llm)

    assert response == "Hello! Nice to meet you."


def test_remember_request_asks_for_confirmation():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message(
        "Lembre-se de que eu gosto de robótica.",
        fake_llm,
    )

    assert "Responda sim ou não" in response
    assert conversation.pending_memory["content"] == (
        "eu gosto de robótica"
    )
    assert conversation.long_term_memory.memories == []
    assert len(fake_llm.calls) == 0


def test_memory_is_saved_after_confirmation():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.send_message(
        "Lembre-se de que eu gosto de robótica.",
        fake_llm,
    )

    response = conversation.send_message("Sim", fake_llm)

    assert "Salvei" in response
    assert len(conversation.long_term_memory.memories) == 1
    assert conversation.long_term_memory.memories[0]["content"] == (
        "eu gosto de robótica"
    )
    assert conversation.pending_memory is None


def test_memory_is_not_saved_after_rejection():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.send_message(
        "Lembre-se de que eu gosto de robótica.",
        fake_llm,
    )

    response = conversation.send_message("Não", fake_llm)

    assert "Não vou salvar" in response
    assert conversation.long_term_memory.memories == []
    assert conversation.pending_memory is None


def test_remember_request_works_in_english():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message(
        "Remember that I like robotics.",
        fake_llm,
    )

    assert "answer yes or no" in response
    assert conversation.pending_memory["content"] == (
        "I like robotics"
    )


def test_forget_request_asks_for_confirmation_before_deleting():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.long_term_memory.add_memory(
        "User likes Python programming."
    )

    response = conversation.send_message(
        "Esqueça que eu gosto de Python.",
        fake_llm,
    )

    assert "Responda sim ou não" in response
    assert len(conversation.long_term_memory.memories) == 1

    response = conversation.send_message("Sim", fake_llm)

    assert "excluída" in response
    assert conversation.long_term_memory.memories == []
    assert len(fake_llm.calls) == 0


def test_forget_request_is_cancelled_when_user_says_no():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    conversation.long_term_memory.add_memory(
        "User likes Python programming."
    )

    conversation.send_message("Esqueça que eu gosto de Python.", fake_llm)
    response = conversation.send_message("Não", fake_llm)

    assert "não vou excluir" in response.lower()
    assert len(conversation.long_term_memory.memories) == 1


def test_forget_request_does_not_delete_when_nothing_matches():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message(
        "Esqueça que eu gosto de astronomia.",
        fake_llm,
    )

    assert "Não encontrei" in response
    assert conversation.long_term_memory.memories == []

def test_date_question_is_answered_without_calling_the_llm():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message("Que dia é hoje?", fake_llm)

    assert response.startswith("Hoje é")
    assert len(fake_llm.calls) == 0


def test_tomorrow_question_is_answered_without_calling_the_llm():
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message("Que dia é amanhã?", fake_llm)

    assert response.startswith("Amanhã será")
    assert len(fake_llm.calls) == 0


@pytest.mark.parametrize("message", [
    "O que eu tenho pra fazer hoje?",
    "Estou cansada hoje.",
    "Em 3 dias tenho prova.",
    "Que dia horrível hoje!",
])
def test_messages_that_only_mention_a_date_reach_the_llm(message):
    conversation = Conversation("You are AISSY.")
    fake_llm = FakeLLM()

    response = conversation.send_message(message, fake_llm)

    assert response == "Hello! Nice to meet you."
    assert len(fake_llm.calls) == 1