"""Constantes partilhadas por todos os agentes."""

DOMINIO = "localhost"
PASSWORD = "password"


def jid(nome):
    return f"{nome}@{DOMINIO}"


# Parâmetros da barragem
NIVEL_ALERTA_RESERVATORIO = 80.0   # % a partir da qual é preciso descarregar
CAPACIDADE_RESERVATORIO = 10000.0  # volume que corresponde a 100% de enchimento
PERIODO_MONITORIZACAO = 10         # segundos entre verificações do reservatório
TEMPO_ESPERA_VOTOS = 3             # segundos à espera da resposta dos líderes

# Parâmetros dos bairros
PERIODO_MEDICAO = 5                # segundos entre medições do operador de bairro
CAPACIDADE_TANQUE = 100.0          # nível de água que o bairro consegue reter
FATOR_CHEIA = 1.0                  # quanto o nível sobe por cada unidade de caudal libertado
# nível de água (%) até ao qual cada risco se aplica; acima de 75 é "crítico"
LIMITES_RISCO = [(25.0, "baixo"), (50.0, "moderado"), (75.0, "elevado")]
# efeito de cada recurso a reduzir o nível de água do bairro
EFEITO_RECURSO = {"bombas": 5.0, "barreiras": 3.0, "equipas": 2.0}
# recursos que o líder pede, conforme o risco do bairro
RECURSOS_POR_RISCO = {
    "baixo": {},
    "moderado": {"bombas": 1},
    "elevado": {"bombas": 2, "barreiras": 1},
    "crítico": {"bombas": 3, "barreiras": 2, "equipas": 1},
}
# caudal máximo que o líder aceita da barragem, conforme o risco do bairro
CAUDAL_ACEITE = {"baixo": 80.0, "moderado": 50.0, "elevado": 25.0, "crítico": 0.0}
