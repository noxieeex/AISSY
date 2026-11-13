"""
Treina e avalia o classificador de idioma.

Uso (na raiz do projeto):  python -m evaluation.train_language

Separa os exemplos em treino e teste (1 a cada 4 vai para o teste), treina só
com o treino e compara, no TESTE, a heurística antiga, o modelo treinado e a
combinação dos dois. O modelo salvo é exatamente o que foi avaliado.
"""

import sys
from pathlib import Path

from aissy.conversation import heuristic_language
from aissy.language_model import LanguageModel, MODEL_PATH, save_model, train

DATA = Path(__file__).parent / "data" / "language_samples.tsv"
HOLDOUT = Path(__file__).parent / "data" / "language_holdout.tsv"
CONFIDENCE = 0.75


def load_samples(path=DATA):
    samples = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            label, text = line.split("\t", 1)
            samples.append((label, text))

    return samples


def split(samples):
    """Divisão determinística: dentro de cada idioma, todo 4º exemplo é teste."""
    train_set, test_set, seen = [], [], {}

    for label, text in samples:
        index = seen.get(label, 0)
        seen[label] = index + 1
        (test_set if index % 4 == 3 else train_set).append((label, text))

    return train_set, test_set


def accuracy(predict, test_set):
    errors = [(text, label, predict(text)) for label, text in test_set if predict(text) != label]
    return 1 - len(errors) / len(test_set), errors


def main():
    samples = load_samples()
    train_set, test_set = split(samples)
    model = LanguageModel(train(train_set))

    def trained(text):
        return model.predict(text)[0]

    def combined(text):
        label, confidence = model.predict(text)
        return label if confidence >= CONFIDENCE else heuristic_language(text)

    print(f"Exemplos: {len(train_set)} treino, {len(test_set)} teste")

    results = {}

    for name, predict in (
        ("heurística antiga", heuristic_language),
        ("modelo treinado", trained),
        ("modelo + heurística", combined),
    ):
        score, errors = accuracy(predict, test_set)
        results[name] = errors
        print(f"{name:22s} acerto no teste: {score:6.1%} ({len(errors)} erros)")

    holdout = load_samples(HOLDOUT)
    print(f"\nConjunto extra, escrito à parte e nunca usado no treino ({len(holdout)} frases, muitas bem curtas):")

    for name, predict in (
        ("heurística antiga", heuristic_language),
        ("modelo treinado", trained),
        ("modelo + heurística", combined),
    ):
        score, errors = accuracy(predict, holdout)
        print(f"{name:22s} acerto: {score:6.1%} ({len(errors)} erros)")

        if name == "modelo + heurística":
            for text, expected, got in errors:
                print(f"    esperado {expected:5s} obtido {got:5s} | {text}")

    print("\nErros do modelo + heurística no teste:")

    for text, expected, got in results["modelo + heurística"]:
        print(f"  esperado {expected:5s} obtido {got:5s} | {text}")

    save_model(train(train_set))
    print(f"\nModelo salvo em {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
