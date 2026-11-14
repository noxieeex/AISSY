# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import argparse
import tempfile
from pathlib import Path

from aissy.embeddings import OllamaEmbedder
from aissy.long_term_memory import LongTermMemory
from evaluation.retrieval_cases import CASES, MEMORIES

THRESHOLDS = (0.0, 0.3, 0.4, 0.5, 0.6)
TOP_K = 3


class CachedEmbedder:
    """Evita recalcular o embedding de um mesmo texto durante a avaliação."""

    def __init__(self, embedder):
        self.embedder = embedder
        self.model = embedder.model
        self.cache = {}

    def embed(self, texts):
        missing = [text for text in dict.fromkeys(texts) if text not in self.cache]

        if missing:
            for text, vector in zip(missing, self.embedder.embed(missing)):
                self.cache[text] = vector

        return [self.cache[text] for text in texts]


def build_memory(database_path, embedder):
    memory = LongTermMemory(database_path, embedder=embedder)
    key_by_id = {}

    for item in MEMORIES:
        memory_id = memory.add_memory(
            item["content"],
            category=item.get("category", "general"),
        )
        key_by_id[memory_id] = item["key"]

    return memory, key_by_id


def score(search, key_by_id):
    hit_1 = hit_3 = with_answer = false_positives = without_answer = 0

    for case in CASES:
        keys = [key_by_id[item["id"]] for item in search(case["query"])]
        expected = case["expected"]

        if expected is None:
            without_answer += 1
            if keys:
                false_positives += 1
            continue

        with_answer += 1

        if keys[:1] == [expected]:
            hit_1 += 1

        if expected in keys[:TOP_K]:
            hit_3 += 1

    return hit_1, hit_3, with_answer, false_positives, without_answer


def report(name, result):
    hit_1, hit_3, with_answer, false_positives, without_answer = result
    print(
        f"{name:<30} hit@1 {hit_1}/{with_answer}   "
        f"hit@3 {hit_3}/{with_answer}   "
        f"falsos positivos {false_positives}/{without_answer}",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="bge-m3")
    args = parser.parse_args()

    embedder = CachedEmbedder(OllamaEmbedder(model=args.model))

    with tempfile.TemporaryDirectory() as folder:
        print("Carregando o modelo e indexando as memórias...", flush=True)

        memory, key_by_id = build_memory(Path(folder) / "eval.db", embedder)
        memory.index_missing()

        print(
            f"Modelo: {args.model} | {len(MEMORIES)} memórias | "
            f"{len(CASES)} perguntas\n",
            flush=True,
        )

        report(
            "lexical (busca atual)",
            score(lambda q: memory.search_memories(q, limit=TOP_K), key_by_id),
        )

        for threshold in THRESHOLDS:
            report(
                f"semântica (limiar {threshold})",
                score(
                    lambda q, t=threshold: memory.semantic_search(
                        q, limit=TOP_K, min_similarity=t
                    ),
                    key_by_id,
                ),
            )

        for threshold in THRESHOLDS:
            report(
                f"híbrida (limiar {threshold})",
                score(
                    lambda q, t=threshold: memory.retrieve_memories(
                        q, limit=TOP_K, min_similarity=t
                    ),
                    key_by_id,
                ),
            )


if __name__ == "__main__":
    main()