"""Recolha das métricas de avaliação (secção 7 do guia).

Métricas recolhidas:

- tempo de deteção: ciclos entre um bairro chegar de facto a risco elevado
  (calculado no ambiente com as regras de risco.py) e o operador alertar;
- mensagens trocadas, por performativa;
- tempo até à decisão coletiva: segundos entre a proposta da barragem e o
  resultado da votação;
- utilização dos recursos de mitigação, por bairro;
- evolução do risco: nível, velocidade e risco de cada bairro em cada ciclo;
- propostas aprovadas, rejeitadas na votação e rejeitadas por segurança;
- transações entre bairros e preços negociados.

Uso: `main.py` chama `iniciar()` no arranque, `registar_ciclo()` a cada passo
do ambiente e `exportar()` no fim. Os agentes chamam os ganchos (`alerta`,
`mitigacao`, `proposta`, `decisao`, `rejeitada_seguranca`, `descarga`,
`transacao`). Sem `iniciar()` os ganchos não fazem nada, por isso os agentes
funcionam também fora de uma simulação (por exemplo, nos testes).

As mensagens contam-se sem mexer nos agentes: `instalar_contador_mensagens()`
embrulha o método `send` dos behaviours do SPADE (todos o herdam de
CyclicBehaviour).

Ficheiros exportados para a pasta do cenário:
    ciclos.csv    uma linha por ciclo do ambiente
    eventos.csv   alertas, mitigações, propostas, decisões, descargas...
    resumo.json   os totais de cada métrica
"""

import csv
import json
import os
import time
from collections import Counter

from config import PERIODO_CICLO
from risco import classificar_risco

RISCOS_ALTOS = ("elevado", "crítico")


class Recolha:
    """Métricas de uma execução de um cenário.

    Args:
        cenario: nome do cenário (fica no resumo).
        ambiente: o Ambiente da simulação, que dá o ciclo atual e o estado.
    """

    def __init__(self, cenario, ambiente):
        """Cria uma recolha vazia.

        Args:
            cenario (str): Nome do cenário (fica no resumo).
            ambiente (ambiente.Ambiente): O ambiente da simulação.
        """
        self.cenario = cenario
        self.ambiente = ambiente
        self.inicio = time.monotonic()
        self.ciclos = []                 # uma linha (dict) por ciclo
        self.eventos = []                # um dict por evento
        self.inicio_risco_real = {}      # bairro -> 1.º ciclo em risco elevado
        self.mensagens = Counter()       # performativa -> quantidade
        self.mensagens_por_agente = Counter()

    # ---- ciclos ----------------------------------------------------------

    def registar_ciclo(self):
        """Guarda o estado do ambiente depois de um passo, com o risco real
        de cada bairro (as mesmas regras que o operador usa)."""
        amb = self.ambiente
        linha = {
            "ciclo": amb.ciclo,
            "segundos": round(self._agora(), 2),
            "chuva": amb.chuva_ultimo_ciclo,
            "reservatorio": round(amb.nivel_reservatorio, 2),
            "caudal_entrada": round(amb.caudal_entrada, 2),
            "caudal_saida": round(amb.caudal_saida, 2),
        }
        for nome, b in amb.bairros.items():
            risco, _ = classificar_risco(
                nivel=b.nivel, velocidade=b.velocidade,
                entrada_chuva=b.entrada_chuva(amb.chuva_ultimo_ciclo),
                drenagem=b.drenagem_natural())
            linha[f"nivel_{nome}"] = round(b.nivel, 2)
            linha[f"velocidade_{nome}"] = round(b.velocidade, 2)
            linha[f"humidade_{nome}"] = round(b.humidade, 3)
            linha[f"risco_{nome}"] = risco
            if risco in RISCOS_ALTOS and nome not in self.inicio_risco_real:
                self.inicio_risco_real[nome] = amb.ciclo
        self.ciclos.append(linha)

    # ---- ganchos chamados pelos agentes ----------------------------------

    def mensagem(self, remetente, performativa):
        """Conta uma mensagem enviada.

        Args:
            remetente (str): Nome do agente que enviou.
            performativa (str | None): Performativa FIPA da mensagem.
        """
        self.mensagens[performativa or "sem performativa"] += 1
        self.mensagens_por_agente[remetente] += 1

    def alerta(self, bairro, risco):
        """O operador do bairro alertou o líder com este risco.

        Args:
            bairro (str): "A", "B" ou "C".
            risco (str): Classe de risco do alerta.
        """
        self._evento("alerta", bairro=bairro, risco=risco)

    def mitigacao(self, bairro, recursos):
        """O operador ativou recursos de mitigação.

        Args:
            bairro (str): "A", "B" ou "C".
            recursos (dict): Quantidade ativada por recurso, como {"bombas": 2}.
        """
        self._evento("mitigacao", bairro=bairro, recursos=dict(recursos))

    def proposta(self, caudal):
        """A barragem enviou um plano de descarga aos líderes.

        Args:
            caudal (float): Caudal proposto.
        """
        self._evento("proposta", caudal=caudal)

    def decisao(self, aprovado, favoraveis, total):
        """Resultado da votação da última proposta.

        Args:
            aprovado (bool): Se a proposta foi aprovada.
            favoraveis (int): Votos a favor.
            total (int): Número de votantes.
        """
        self._evento("decisao", aprovado=aprovado, favoraveis=favoraveis, total=total)

    def rejeitada_seguranca(self, motivo=""):
        """A barragem rejeitou um plano por não respeitar os limites de segurança.

        Args:
            motivo (str): Porque foi rejeitado.
        """
        self._evento("rejeitada_seguranca", motivo=motivo)

    def descarga(self, caudal, duracao):
        """A barragem executou uma descarga.

        Args:
            caudal (float): Caudal libertado.
            duracao (int): Ciclos de duração.
        """
        self._evento("descarga", caudal=caudal, duracao=duracao)

    def transacao(self, comprador, fornecedor, servico, quantidade, preco):
        """Um contrato entre bairros foi pago (Contract Net).

        Args:
            comprador (str): Bairro que pagou.
            fornecedor (str): Bairro que forneceu.
            servico (str): Serviço contratado, como "bombas".
            quantidade (int): Unidades contratadas.
            preco (float): Preço por unidade.
        """
        self._evento("transacao", comprador=comprador, fornecedor=fornecedor,
                     servico=servico, quantidade=quantidade, preco=preco)

    # ---- resultados ------------------------------------------------------

    def resumo(self):
        """Devolve os totais de todas as métricas num dicionário.

        Returns:
            dict: O conteúdo do `resumo.json` (deteção, mensagens, tempo até
            à decisão, propostas, recursos, transações e níveis).
        """
        bairros = list(self.ambiente.bairros)
        por_tipo = {}
        for e in self.eventos:
            por_tipo.setdefault(e["tipo"], []).append(e)

        deteccao = {}
        for b in bairros:
            inicio = self.inicio_risco_real.get(b)
            alertas = [e["ciclo"] for e in por_tipo.get("alerta", [])
                       if e["bairro"] == b and e["risco"] in RISCOS_ALTOS
                       and inicio is not None and e["ciclo"] >= inicio]
            deteccao[b] = alertas[0] - inicio if alertas else None

        tempos_decisao, pendente = [], None
        for e in self.eventos:
            if e["tipo"] == "proposta":
                pendente = e["segundos"]
            elif e["tipo"] == "decisao" and pendente is not None:
                tempos_decisao.append(round(e["segundos"] - pendente, 4))
                pendente = None

        recursos_bairro = {b: Counter() for b in bairros}
        for e in por_tipo.get("mitigacao", []):
            recursos_bairro[e["bairro"]].update(e["recursos"])
        total_recursos = sum(recursos_bairro.values(), Counter())

        precos = {}
        for e in por_tipo.get("transacao", []):
            precos.setdefault(e["servico"], []).append(e["preco"])

        decisoes = por_tipo.get("decisao", [])
        return {
            "cenario": self.cenario,
            "ciclos": len(self.ciclos),
            "duracao_s": round(self._agora(), 1),
            "tempo_deteccao_ciclos": deteccao,
            "tempo_deteccao_s": {b: (None if c is None else c * PERIODO_CICLO)
                                 for b, c in deteccao.items()},
            "mensagens": {"total": sum(self.mensagens.values()),
                          "por_performativa": dict(self.mensagens),
                          "por_agente": dict(self.mensagens_por_agente)},
            "tempo_ate_decisao_s": tempos_decisao,
            "propostas": {
                "total": len(por_tipo.get("proposta", [])),
                "aprovadas": sum(1 for e in decisoes if e["aprovado"]),
                "rejeitadas_votacao": sum(1 for e in decisoes if not e["aprovado"]),
                "rejeitadas_seguranca": len(por_tipo.get("rejeitada_seguranca", [])),
                "descargas": len(por_tipo.get("descarga", [])),
            },
            "recursos": {"total": dict(total_recursos),
                         "por_bairro": {b: dict(c) for b, c in recursos_bairro.items()}},
            "transacoes": {"total": len(por_tipo.get("transacao", [])),
                           "preco_medio": {s: round(sum(p) / len(p), 2)
                                           for s, p in precos.items()}},
            "alertas": len(por_tipo.get("alerta", [])),
            "nivel_maximo": {b: max((l[f"nivel_{b}"] for l in self.ciclos), default=0.0)
                             for b in bairros},
            "ciclos_em_risco_elevado": {
                b: sum(1 for l in self.ciclos if l[f"risco_{b}"] in RISCOS_ALTOS)
                for b in bairros},
        }

    def exportar(self, pasta):
        """Escreve ciclos.csv, eventos.csv e resumo.json em `pasta`.

        Args:
            pasta (str): Pasta de destino (criada se não existir).
        """
        os.makedirs(pasta, exist_ok=True)
        if self.ciclos:
            with open(os.path.join(pasta, "ciclos.csv"), "w", newline="",
                      encoding="utf-8") as f:
                escritor = csv.DictWriter(f, fieldnames=list(self.ciclos[0]))
                escritor.writeheader()
                escritor.writerows(self.ciclos)
        with open(os.path.join(pasta, "eventos.csv"), "w", newline="",
                  encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow(["ciclo", "segundos", "tipo", "bairro", "detalhe"])
            for e in self.eventos:
                extra = {k: v for k, v in e.items()
                         if k not in ("ciclo", "segundos", "tipo", "bairro")}
                escritor.writerow([e["ciclo"], e["segundos"], e["tipo"],
                                   e.get("bairro", ""), json.dumps(extra, ensure_ascii=False)])
        with open(os.path.join(pasta, "resumo.json"), "w", encoding="utf-8") as f:
            json.dump(self.resumo(), f, ensure_ascii=False, indent=2)

    # ---- interno ---------------------------------------------------------

    def _agora(self):
        """Segundos desde o início da recolha."""
        return time.monotonic() - self.inicio

    def _evento(self, tipo, **dados):
        """Guarda um evento com o ciclo e o instante em que aconteceu.

        Args:
            tipo (str): Tipo do evento, como "alerta" ou "descarga".
            **dados: Campos próprios do evento.
        """
        self.eventos.append({"ciclo": self.ambiente.ciclo,
                             "segundos": round(self._agora(), 4),
                             "tipo": tipo, **dados})


# ---- recolha da simulação em curso (funções usadas pelos agentes) ----------

_atual = None


def iniciar(cenario, ambiente):
    """Começa uma recolha nova para o cenário e o ambiente dados.

    Args:
        cenario (str): Nome do cenário.
        ambiente (ambiente.Ambiente): O ambiente da simulação.

    Returns:
        Recolha: A recolha criada, que passa a ser a recolha em curso.
    """
    global _atual
    _atual = Recolha(cenario, ambiente)
    return _atual


def terminar():
    """Esquece a recolha atual (os ganchos voltam a não fazer nada)."""
    global _atual
    _atual = None


def atual():
    """A recolha em curso, ou None.

    Returns:
        Recolha | None: A recolha iniciada por `iniciar`, se ainda não foi
        terminada.
    """
    return _atual


def _gancho(nome):
    """Cria a função do módulo que passa a chamada ao método `nome` da
    recolha em curso, e não faz nada se não houver nenhuma."""
    def chamar(*args, **kwargs):
        """Chama o método da recolha em curso, se houver."""
        if _atual is not None:
            getattr(_atual, nome)(*args, **kwargs)
    chamar.__name__ = nome
    chamar.__doc__ = f"Passa para Recolha.{nome} se houver uma recolha em curso."
    return chamar


registar_ciclo = _gancho("registar_ciclo")
mensagem = _gancho("mensagem")
alerta = _gancho("alerta")
mitigacao = _gancho("mitigacao")
proposta = _gancho("proposta")
decisao = _gancho("decisao")
rejeitada_seguranca = _gancho("rejeitada_seguranca")
descarga = _gancho("descarga")
transacao = _gancho("transacao")


def instalar_contador_mensagens(classe_behaviour=None):
    """Passa a contar todas as mensagens enviadas pelos behaviours.

    Embrulha `send` de `classe_behaviour` (por omissão o CyclicBehaviour do
    SPADE, de onde todos os behaviours herdam). Chamar duas vezes não
    conta a dobrar.

    Args:
        classe_behaviour (type | None): Classe cujo `send` se embrulha.
    """
    if classe_behaviour is None:
        from spade.behaviour import CyclicBehaviour
        classe_behaviour = CyclicBehaviour
    original = classe_behaviour.send
    if getattr(original, "_conta_mensagens", False):
        return

    async def send(self, msg):
        """Conta a mensagem e envia-a com o `send` original do SPADE.

        Args:
            msg (Message): A mensagem a enviar.

        Returns:
            O resultado do `send` original.
        """
        agente = getattr(getattr(self, "agent", None), "name", "?")
        mensagem(str(agente), msg.get_metadata("performative"))
        return await original(self, msg)

    send._conta_mensagens = True
    classe_behaviour.send = send
