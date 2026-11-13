import json
from pathlib import Path

import pytest

from aissy.conversation import detect_language, heuristic_language
from aissy.language_model import (
    LanguageModel,
    extract_ngrams,
    load_model,
    save_model,
    train,
)

HOLDOUT = Path(__file__).parent.parent / "evaluation" / "data" / "language_holdout.tsv"


def test_extract_ngrams_marks_word_borders():
    grams = extract_ngrams("Oi")

    assert " o" in grams and "i " in grams and "oi" in grams


def test_tiny_model_learns_its_examples():
    model = LanguageModel(
        train([("pt-BR", "obrigada pela ajuda"), ("en", "thanks for the help"), ("es", "gracias por la ayuda")])
    )

    assert model.predict("obrigada pela ajuda")[0] == "pt-BR"
    assert model.predict("thanks for the help")[0] == "en"
    assert model.predict("gracias por la ayuda")[0] == "es"


def test_probabilities_sum_to_one():
    model = LanguageModel(train([("pt-BR", "oi"), ("en", "hi"), ("es", "hola")]))

    assert sum(model.scores("oi").values()) == pytest.approx(1.0)


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "model.json"
    save_model(train([("pt-BR", "oi tudo bem"), ("en", "hi there"), ("es", "hola qué tal")]), path)

    assert load_model(path).predict("hi there")[0] == "en"


@pytest.mark.parametrize("content", [None, "not json", "[]", '{"labels": 1}'])
def test_load_model_returns_none_for_bad_files(tmp_path, content):
    path = tmp_path / "model.json"

    if content is not None:
        path.write_text(content, encoding="utf-8")

    assert load_model(path) is None


def test_shipped_model_is_valid_json_and_loads():
    from aissy.language_model import MODEL_PATH

    assert json.loads(MODEL_PATH.read_text(encoding="utf-8"))["labels"]
    assert load_model() is not None


def test_shipped_model_beats_old_heuristic_on_holdout():
    rows = [line.split("\t", 1) for line in HOLDOUT.read_text(encoding="utf-8").splitlines() if line]

    def score(predict):
        return sum(predict(text) == label for label, text in rows) / len(rows)

    assert score(detect_language) >= 0.88
    assert score(detect_language) > score(heuristic_language)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("abre o spotify", "pt-BR"),
        ("what is the date today", "en"),
        ("¿qué hora es?", "es"),
    ],
)
def test_detect_language_on_clear_sentences(text, expected):
    assert detect_language(text) == expected
