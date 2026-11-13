"""
Classificador de idioma treinado (Naive Bayes sobre n-gramas de caracteres).

Escrito em Python puro, sem dependências: o "modelo" é só um arquivo JSON com
contagens, então dá para abrir, ler e entender. Não usa pickle (carregar
pickle de fonte desconhecida pode executar código).

Treino: evaluation/train_language.py
"""

import json
import math
import re
from collections import Counter
from pathlib import Path

LABELS = ("pt-BR", "en", "es")
NGRAM_SIZES = (1, 2, 3)
ALPHA = 0.5  # suavização: n-grama nunca visto não zera a probabilidade
MODEL_PATH = Path(__file__).parent / "models" / "language_model.json"


def extract_ngrams(text):
    """Texto -> lista de n-gramas de caracteres (com bordas marcadas)."""
    cleaned = re.sub(r"\s+", " ", text.lower().strip())
    padded = f" {cleaned} "
    grams = []

    for size in NGRAM_SIZES:
        for start in range(len(padded) - size + 1):
            grams.append(padded[start:start + size])

    return grams


def train(samples):
    """samples: lista de (rótulo, texto). Devolve o modelo como dicionário."""
    counts = {label: Counter() for label in LABELS}

    for label, text in samples:
        counts[label].update(extract_ngrams(text))

    vocabulary = sorted({gram for c in counts.values() for gram in c})

    return {
        "labels": list(LABELS),
        "alpha": ALPHA,
        "vocabulary_size": len(vocabulary),
        "counts": {label: dict(counts[label]) for label in LABELS},
    }


class LanguageModel:
    def __init__(self, model):
        self.labels = model["labels"]
        self.alpha = model["alpha"]
        self.vocabulary_size = model["vocabulary_size"]
        self.counts = model["counts"]
        self.totals = {
            label: sum(self.counts[label].values()) for label in self.labels
        }

    def scores(self, text):
        grams = extract_ngrams(text)
        log_scores = {}

        for label in self.labels:
            counts = self.counts[label]
            denominator = self.totals[label] + self.alpha * self.vocabulary_size
            log_scores[label] = sum(
                math.log((counts.get(gram, 0) + self.alpha) / denominator)
                for gram in grams
            )

        # softmax estável: vira probabilidades que somam 1
        best = max(log_scores.values())
        exps = {k: math.exp(v - best) for k, v in log_scores.items()}
        total = sum(exps.values())

        return {k: v / total for k, v in exps.items()}

    def predict(self, text):
        """Devolve (idioma, confiança entre 0 e 1)."""
        probabilities = self.scores(text)
        label = max(probabilities, key=probabilities.get)

        return label, probabilities[label]


def save_model(model, path=MODEL_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")


def load_model(path=MODEL_PATH):
    """Carrega o modelo treinado; devolve None se não existir ou estiver inválido."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return LanguageModel(data)
    except (OSError, ValueError, KeyError, TypeError):
        return None
