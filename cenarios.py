"""Cenários: só dados (estado inicial do sistema). Sem lógica de agentes.

Cada cenário define o nível inicial do reservatório (%) e o nível de água
inicial de cada bairro. Por agora só existe o cenário "calmo", que
reproduz o comportamento anterior (tudo a zero).
"""

CENARIOS = {
    "calmo": {
        "reservatorio": 0.0,
        "bairros": {"A": 0.0, "B": 0.0, "C": 0.0},
    },
    "cheia": {
        "reservatorio": 90.0,
        "bairros": {"A": 10.0, "B": 30.0, "C": 60.0},
    },
}

CENARIO_POR_OMISSAO = "cheia"


def aplicar_cenario(nome, barragem, operadores):
    """Define o estado inicial dos agentes segundo o cenário escolhido."""
    cenario = CENARIOS[nome]
    barragem.nivel_reservatorio = cenario["reservatorio"]
    for op in operadores:
        op.nivel_agua = cenario["bairros"][op.bairro]
