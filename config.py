"""Constantes partilhadas por todos os agentes."""

DOMINIO = "localhost"
PASSWORD = "password"


def jid(nome):
    return f"{nome}@{DOMINIO}"


# Parâmetros da barragem
NIVEL_ALERTA_RESERVATORIO = 80.0   # % a partir da qual é preciso descarregar
CAPACIDADE_RESERVATORIO = 5000.0   # volume que corresponde a 100% de enchimento
                                   # (com 10000 uma descarga de 50 nunca vencia a chuva)
PERIODO_MONITORIZACAO = 10         # segundos entre verificações do reservatório
TEMPO_ESPERA_VOTOS = 3             # segundos à espera da resposta dos líderes
MAX_RODADAS = 3                    # rodadas de negociação da descarga (N_max do guia)
DURACAO_DESCARGA = 20              # ciclos de uma descarga (normal ou de contingência)
# Contingência (secção 5.2 do guia): procedimento pré-definido da barragem
NIVEL_CONTINGENCIA_RESERVATORIO = 90.0  # % a partir da qual, sem acordo, aplica-se
NIVEL_EMERGENCIA_RESERVATORIO = 95.0    # % a partir da qual aplica-se logo, sem negociar
FRACAO_CAUDAL_CONTINGENCIA = 0.75       # caudal da contingência, em fração do máximo seguro
ESPERA_INICIAL = 8                 # segundos até a barragem fazer a 1.ª verificação
                                   # (dá tempo aos alertas dos bairros chegarem aos líderes)

# Parâmetros dos bairros
PERIODO_MEDICAO = 10               # segundos entre medições do operador de bairro
                                   # (com 5 s o risco oscilava e gerava muitos alertas)
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
CAUDAL_BASE_ENTRADA = 8.0          # caudal que entra no reservatório sem chuva
AREA_BACIA = 3.0                   # caudal de entrada extra por mm de chuva
                                   # (com 4 mm entram 20 por ciclo; as descargas
                                   # propostas, de 25 a 60, passam a baixar o nível)
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

# Mercado de serviços entre bairros (secções 3 e 5.3 do guia, regras 7 a 10
# do modelo Gaia). Moeda e preços são fictícios.
#
# Preço base de cada serviço, por unidade (nos sacos de areia, por lote).
# O guia só dá sacos de areia, bomba e equipa; o preço das barreiras é um
# valor fictício escolhido pela equipa, para também poderem ser contratadas.
PRECO_BASE = {
    "sacos_areia": 10.0,
    "bombas": 20.0,
    "equipas": 30.0,
    "barreiras": 15.0,
}
# Reserva mínima (regra 7): um bairro só oferece um recurso se, depois de o
# vender, ainda ficar com pelo menos isto em estoque livre
# (estoque - reservado - quantidade >= RESERVA_MINIMA).
RESERVA_MINIMA = {"bombas": 1, "sacos_areia": 2, "barreiras": 1, "equipas": 1}
# "Condições adequadas" para oferecer (secção 3 do guia): um bairro em risco
# elevado ou crítico guarda os recursos para si e não vende.
RISCOS_QUE_PERMITEM_OFERECER = ("baixo", "moderado")
# Riscos que levam o líder a contratar o que falta no estoque local
# (atividade IdentificarNecessidade do papel Comprador).
RISCOS_QUE_PEDEM_CONTRATACAO = ("elevado", "crítico")
FRACAO_ABERTURA_COMPRADOR = 0.6    # o comprador abre com 60% do preço base
FRACAO_MINIMA_VENDEDOR = 0.7       # o vendedor aceita a partir de 70% do preço base
MAX_RODADAS_CN = 3                 # rodadas de contraproposta no Contract Net
TEMPO_ESPERA_CN = 3                # segundos à espera de cada resposta no Contract Net
TEMPO_ESPERA_EXECUCAO = 10         # segundos à espera da confirmação do serviço
PERIODO_OFERTAS = 5                # segundos entre revisões das ofertas no diretório


# Experimentos (experimentos.py): a variável de ambiente FLOOD_PARAMETROS, em
# JSON, muda constantes deste ficheiro sem o editar, por exemplo
# {"MAX_RODADAS": 1}. Tem de ficar no fim, depois de todas as constantes.
import json as _json
import os as _os

for _nome, _valor in _json.loads(_os.environ.get("FLOOD_PARAMETROS") or "{}").items():
    globals()[_nome] = _valor
