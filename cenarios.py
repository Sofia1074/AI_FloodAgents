"""Cenários: só dados (estado inicial e chuva prevista). Sem lógica de agentes.

Cada cenário define:
    reservatorio  nível inicial do reservatório (%)
    chuva         mm de chuva em cada ciclo do ambiente (depois do fim, não chove)
    bairros       estado inicial de cada bairro (ver Bairro em ambiente.py)

Os três primeiros são os cenários de avaliação do guia (secção 7).
"calmo" e "cheia" são estados de teste.

Os bairros têm características fixas (_BAIRROS), como pede o guia:
    A  junto ao rio: recebe mais água da descarga, drenagem fraca
    B  centro: ruas impermeáveis, mais população, boa drenagem
    C  zona alta: pouca água da descarga, solo que absorve bem
"""

_ESTOQUE_NORMAL = {"bombas": 3, "sacos_areia": 5, "barreiras": 2, "equipas": 1}
# estoque de sobra: o bairro mitiga sozinho e não precisa de contratar
_ESTOQUE_FARTO = {"bombas": 8, "sacos_areia": 5, "barreiras": 4, "equipas": 2}

_BAIRROS = {
    "A": {"exposicao": 0.05, "drenagem": 2.0, "fator_chuva": 0.6, "populacao": 4000},
    "B": {"exposicao": 0.04, "drenagem": 3.0, "fator_chuva": 0.5, "populacao": 9000},
    "C": {"exposicao": 0.02, "drenagem": 2.5, "fator_chuva": 0.4, "populacao": 2500},
}


def _bairro(nome, nivel, humidade=0.3, estoque=None, moeda=100.0, **alteracoes):
    """Junta as características fixas do bairro com o estado do cenário."""
    dados = dict(_BAIRROS[nome], nivel=nivel, humidade=humidade,
                 estoque=dict(estoque if estoque is not None else _ESTOQUE_NORMAL),
                 moeda=moeda)
    dados.update(alteracoes)
    return dados


CENARIOS = {
    # 1. Risco elevado num bairro: chuva forte e o bairro A, com o solo já
    #    molhado e a drenagem entupida, sobe depressa. O operador deteta a
    #    subida rápida e o líder pede mitigação. O reservatório fica abaixo
    #    do alerta, por isso a barragem não entra.
    "risco_elevado": {
        "reservatorio": 55.0,
        "chuva": [1, 1, 2] + [8] * 6 + [3, 2, 1],
        "bairros": {
            "A": _bairro("A", nivel=15.0, humidade=0.6, drenagem=1.0,
                         estoque=_ESTOQUE_FARTO),
            "B": _bairro("B", nivel=5.0),
            "C": _bairro("C", nivel=5.0, humidade=0.2),
        },
    },

    # 2. Conflito de interesses: o reservatório passa o alerta e a chuva
    #    continua, por isso a barragem tem de descarregar. O bairro A, junto
    #    ao rio e já em risco moderado, quer pouco caudal porque a descarga
    #    lhe chega primeiro; B está seguro e aceita; C, em risco moderado,
    #    aceita um caudal médio. Há negociação e a votação decide por
    #    maioria. Sem descarga o reservatório passa dos 95% e a barragem
    #    aplica a contingência; com descarga baixa, à custa do bairro A.
    #    (Os números foram calibrados com uma simulação só do ambiente: sem
    #    mitigação o A chega a risco elevado e, com ela, deve aguentar.)
    "conflito": {
        "reservatorio": 88.0,
        "chuva": [4] * 14,
        "bairros": {
            "A": _bairro("A", nivel=55.0, humidade=0.5, estoque=_ESTOQUE_FARTO),
            "B": _bairro("B", nivel=15.0),
            "C": _bairro("C", nivel=35.0),
        },
    },

    # 3. Recursos limitados: o bairro B chega a risco elevado sem bombas no
    #    estoque e tem de as contratar a A ou C, que estão seguros e têm
    #    estoque (FIPA Contract Net). A chuva é curta, para B só precisar de
    #    contratar uma vez.
    "recursos_limitados": {
        "reservatorio": 60.0,
        "chuva": [4] * 8 + [1] * 2,
        "bairros": {
            "A": _bairro("A", nivel=10.0),
            "B": _bairro("B", nivel=50.0, humidade=0.7,
                         estoque={"bombas": 0, "sacos_areia": 0, "barreiras": 1, "equipas": 1}),
            "C": _bairro("C", nivel=5.0),
        },
    },

    # Estados de teste
    "calmo": {
        "reservatorio": 0.0,
        "chuva": [],
        "bairros": {b: _bairro(b, nivel=0.0, humidade=0.0) for b in "ABC"},
    },
    "cheia": {
        "reservatorio": 90.0,
        "chuva": [],
        "bairros": {
            "A": _bairro("A", nivel=10.0),
            "B": _bairro("B", nivel=30.0),
            "C": _bairro("C", nivel=60.0),
        },
    },
}

CENARIO_POR_OMISSAO = "risco_elevado"
