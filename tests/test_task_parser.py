# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

from datetime import date

import pytest

from aissy.task_parser import parse_task_request

# 11/11/2026 é quarta-feira.
TODAY = date(2026, 11, 11)


@pytest.mark.parametrize(
    "text, title, due",
    [
        ("me lembra de ligar pro dentista amanhã às 10h",
         "Ligar pro dentista", "2026-11-12T10:00"),
        ("Me lembra de estudar inglês hoje", "Estudar inglês", "2026-11-11"),
        ("me lembre de pagar a conta às 18:30", "Pagar a conta", "2026-11-11T18:30"),
        ("me lembra de comprar pão depois de amanhã", "Comprar pão", "2026-11-13"),
        ("me lembra de entregar o trabalho na sexta", "Entregar o trabalho", "2026-11-13"),
        ("me lembra de ir na academia na quarta", "Ir na academia", "2026-11-18"),
        ("me lembra de ligar pra mãe em 3 dias", "Ligar pra mãe", "2026-11-14"),
        ("me lembra de regar as plantas", "Regar as plantas", None),
        ("anota tarefa: revisar o README", "Revisar o README", None),
        ("remind me to call mom tomorrow at 3pm", "Call mom", "2026-11-12T15:00"),
        ("add a task to buy milk", "Buy milk", None),
    ],
)
def test_parses_requests(text, title, due):
    assert parse_task_request(text, TODAY) == {"title": title, "due": due}


@pytest.mark.parametrize(
    "text",
    ["oi tudo bem?", "me lembra", "me lembra de amanhã", "que dia é hoje?", "", None, 42],
)
def test_ignores_everything_else(text):
    assert parse_task_request(text, TODAY) is None
