MEMORIES = [
    {"key": "curso", "content": "User studies Computer Engineering at UFU.", "category": "studies"},
    {"key": "hobby", "content": "Gosto de desenhar nas horas livres.", "category": "hobbies"},
]

CASES = [
    {"query": "Qual é o meu curso na universidade?", "expected": "curso"},
    {"query": "What do I do for fun?", "expected": "hobby"},
    {"query": "Qual é a capital da França?", "expected": None},
]