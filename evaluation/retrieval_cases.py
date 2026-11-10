MEMORIES = [
    {"key": "curso", "content": "User studies Computer Engineering at UFU.", "category": "studies"},
    {"key": "linguagens", "content": "Sabe programar em Python, C e JavaScript.", "category": "skills"},
    {"key": "aissy", "content": "Está desenvolvendo uma assistente pessoal chamada AISSY em Python.", "category": "projects"},
    {"key": "pitwall", "content": "Built Pink Pit Wall, a vehicle telemetry dashboard with Flask.", "category": "projects"},
    {"key": "jogos", "content": "Gosta de jogar RPGs e jogos de corrida nas horas livres.", "category": "hobbies"},
    {"key": "cafe", "content": "Prefers tea over coffee in the morning.", "category": "preferences"},
    {"key": "idiomas", "content": "Fluent in English and native in Portuguese.", "category": "languages"},
    {"key": "estagio", "content": "Está se candidatando a um programa de estágio em IA.", "category": "career"},
    {"key": "horario", "content": "Studies better at night, after 8 pm.", "category": "routine"},
    {"key": "musica", "content": "Gosta de ouvir música pop enquanto programa.", "category": "hobbies"},
    {"key": "rag", "content": "Quer aprender mais sobre RAG e embeddings.", "category": "goals"},
    {"key": "equipe", "content": "Faz parte de uma equipe de competição de engenharia na universidade.", "category": "extracurricular"},
]

CASES = [
    # Palavras em comum com a memória
    {"query": "O que eu estudo na UFU?", "expected": "curso"},
    {"query": "Eu uso Python?", "expected": "linguagens"},
    {"query": "Fale sobre a AISSY", "expected": "aissy"},
    {"query": "Tell me about Pink Pit Wall", "expected": "pitwall"},

    # Mesmo sentido, palavras diferentes
    {"query": "Onde eu faço faculdade?", "expected": "curso"},
    {"query": "O que eu bebo de manhã?", "expected": "cafe"},
    {"query": "Qual é o meu melhor horário para estudar?", "expected": "horario"},
    {"query": "Tenho algum objetivo de carreira?", "expected": "estagio"},
    {"query": "What topics do I want to study next?", "expected": "rag"},

    # Entre idiomas
    {"query": "Qual idioma eu falo?", "expected": "idiomas"},
    {"query": "What music do I like while coding?", "expected": "musica"},
    {"query": "Do I belong to any team?", "expected": "equipe"},
    {"query": "Em que projeto de telemetria eu trabalhei?", "expected": "pitwall"},

    # Sem resposta
    {"query": "Qual é a capital da França?", "expected": None},
    {"query": "What is my favorite color?", "expected": None},
    {"query": "Quanto é 2 + 2?", "expected": None},
    {"query": "Qual é o meu animal de estimação?", "expected": None},
]