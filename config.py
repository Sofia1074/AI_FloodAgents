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
MAX_RODADAS = 3                    # rodadas de negociação da descarga (N_max do guia)
DURACAO_DESCARGA = 10              # ciclos de uma descarga (normal ou de contingência)
# Contingência (secção 5.2 do guia): procedimento pré-definido da barragem
NIVEL_CONTINGENCIA_RESERVATORIO = 90.0  # % a partir da qual, sem acordo, aplica-se
NIVEL_EMERGENCIA_RESERVATORIO = 95.0    # % a partir da qual aplica-se logo, sem negociar
FRACAO_CAUDAL_CONTINGENCIA = 0.75       # caudal da contingência, em fração do máximo seguro
ESPERA_INICIAL = 8                 # segundos até a barragem fazer a 1.ª verificação
                                   # (dá tempo aos alertas dos bairros chegarem aos líderes)

# Parâmetros dos bairros
PERIODO_MEDICAO = 5                # segundos entre medições do operador de bairro
CAPACIDADE_TANQUE = 100.0          # nível de água que o bairro consegue reter
# nível de água (%) até ao qual cada risco se aplica; acima de 75 é "crítico"
LIMITES_RISCO = [(25.0, "baixo"), (50.0, "moderado"), (75.0, "elevado")]
LIMIAR_SUBIDA_RAPIDA = 4.0         # subida por ciclo a partir da qual é "rápida"
AGRAVAMENTO_MAXIMO = 1             # classes que os agravantes podem somar ao nível
NIVEL_MINIMO_DRENAGEM = 15.0       # abaixo disto a drenagem fraca não agrava o risco
# efeito de cada recurso no ambiente, por unidade e durante alguns ciclos:
#   drenagem -> água extra escoada por ciclo
#   protecao -> fração da água da descarga que deixa de entrar no bairro
EFEITO_RECURSO = {
    "bombas":      {"drenagem": 2.0, "protecao": 0.0, "ciclos": 6},
    "equipas":     {"drenagem": 1.0, "protecao": 0.0, "ciclos": 10},
    "barreiras":   {"drenagem": 0.0, "protecao": 0.5, "ciclos": 8},
    "sacos_areia": {"drenagem": 0.0, "protecao": 0.3, "ciclos": 10},
}
PROTECAO_MAXIMA = 0.9              # as barreiras nunca bloqueiam toda a água

# Parâmetros do ambiente (ambiente.py). Modelo aproximado, ver limitações lá.
PERIODO_CICLO = 2                  # segundos entre dois passos do ambiente
CAUDAL_BASE_ENTRADA = 20.0         # caudal que entra no reservatório sem chuva
AREA_BACIA = 10.0                  # caudal de entrada extra por mm de chuva
NIVEL_JUSANTE_BASE = 1.0           # nível do rio a jusante sem descarga (m)
FATOR_JUSANTE = 0.02               # metros a mais a jusante por unidade de caudal
HUMIDADE_POR_MM = 0.02             # quanto a humidade do solo sobe por mm de chuva
SECAGEM_SOLO = 0.02                # quanto a humidade desce por ciclo
PERDA_DRENAGEM_SOLO = 0.5          # com o solo encharcado a drenagem cai até metade
# recursos que o líder pede, conforme o risco do bairro
RECURSOS_POR_RISCO = {
    "baixo": {},
    "moderado": {"bombas": 1},
    "elevado": {"bombas": 2, "barreiras": 1},
    "crítico": {"bombas": 3, "barreiras": 2, "equipas": 1},
}
# caudal máximo que o líder aceita da barragem, conforme o risco do bairro
CAUDAL_ACEITE = {"baixo": 80.0, "moderado": 50.0, "elevado": 25.0, "crítico": 0.0}
