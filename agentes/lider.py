"""Agentes 3A, 3B, 3C — Líder comunitário de um bairro (agente BDI).

O líder é um `BDIAgent` (spade_bdi). Divisão de trabalho:

- `lider.asl` (AgentSpeak) decide: crenças sobre o risco e a proposta de
  descarga, desejos e planos.
- Este ficheiro percebe e age: os behaviours do SPADE recebem as mensagens e
  convertem-nas em crenças; as ações `.pedir_mitigacao` e `.responder`
  enviam as mensagens que resultam das decisões.
"""

import unicodedata
from pathlib import Path

from spade.behaviour import CyclicBehaviour
from spade_bdi.bdi import BDIAgent

import mensagens
import registo
from config import PASSWORD, jid
from rede import REDE

FICHEIRO_ASL = str(Path(__file__).with_name("lider.asl"))


def atomo(texto):
    """Converte um texto num átomo do AgentSpeak (sem acentos).

    Args:
        texto (str): Por exemplo "crítico".

    Returns:
        str: Por exemplo "critico".
    """
    sem_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acentos if not unicodedata.combining(c))


class CommunityLeader(BDIAgent):
    """Agentes 3A, 3B, 3C — Líder comunitário de um bairro.

    Attributes:
        nome (str): Nome do agente, como "liderA".
        bairro (str): "A", "B" ou "C".
        rede: Quem pode comunicar com quem (rede.py).
        risco_do_bairro (str): Último risco recebido do operador.
        recursos_pedidos (dict): Último pedido de recursos feito ao operador.
        propostas (dict): Propostas de descarga em análise, por id.
    """

    def __init__(self, nome, bairro, password=PASSWORD):
        super().__init__(jid(nome), password, FICHEIRO_ASL)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.bairro = bairro
        self.risco_do_bairro = "baixo"   # último risco recebido do operador
        self.recursos_pedidos = {}       # bombas, barreiras, equipa...
        self.propostas = {}              # id -> plano da barragem
        self._seq_propostas = 0

    def add_custom_actions(self, actions):
        """Regista as ações que o `lider.asl` pode chamar.

        Args:
            actions: Conjunto de ações do AgentSpeak, preenchido aqui.
        """
        actions.add_procedure(
            ".registar", (str,),
            lambda texto: registo.detalhe(self.nome, texto))
        actions.add_procedure(
            ".pedir_mitigacao", (tuple,),
            lambda pedido: self.pedir_mitigacao(
                {str(p.args[0]): int(p.args[1]) for p in pedido}))
        actions.add_procedure(
            ".responder", (int, None, float),
            lambda id_proposta, decisao, caudal: self.responder(
                id_proposta, str(decisao), caudal))

    class OuvirMensagens(CyclicBehaviour):
        """Recebe alertas do operador do bairro e propostas da barragem e
        transforma-os em crenças do agente BDI."""

        async def run(self):
            lider = self.agent
            msg = mensagens.ler(await self.receive(timeout=1))
            if msg is None:
                return

            if msg.tipo == "alerta_risco":
                lider.risco_do_bairro = msg.corpo["risco"]
                lider.bdi.set_belief("risco", atomo(msg.corpo["risco"]))

            elif msg.tipo == "proposta_descarga":
                if not lider.rede.pode_comunicar(lider.nome, "barragem"):
                    return
                lider._seq_propostas += 1
                id_proposta = lider._seq_propostas
                lider.propostas[id_proposta] = msg      # guarda o thread para responder
                lider.bdi.set_belief("proposta", id_proposta,
                                     float(msg.corpo["caudal"]))

    async def setup(self):
        """Arranca o behaviour que traduz mensagens em crenças.

        O template deixa passar só os alertas dos operadores e as propostas
        de descarga da barragem."""
        registo.detalhe(self.nome, f"agente BDI ativo (bairro {self.bairro})")
        recebe = (mensagens.template(mensagens.ALERTA_RISCO, mensagens.INFORM)
                  | mensagens.template(mensagens.NEGOCIAR_DESCARGA, mensagens.PROPOSE))
        self.add_behaviour(self.OuvirMensagens(), recebe)

    def pedir_mitigacao(self, recursos):
        """Pede ao operador do bairro que ative recursos (ação `.pedir_mitigacao`).

        Args:
            recursos (dict): Quantidade por recurso, como {"bombas": 2}.
        """
        destino = f"op{self.bairro}"
        if not recursos or not self.rede.pode_comunicar(self.nome, destino):
            return
        self.recursos_pedidos = recursos
        self.submit(self.bdi.send(mensagens.criar(
            destino, mensagens.REQUEST, mensagens.PEDIR_MITIGACAO,
            "pedido_mitigacao", recursos=recursos)))
        registo.detalhe(self.nome, f"risco {self.risco_do_bairro}: "
                                   f"pediu recursos {recursos}")

    def responder(self, id_proposta, decisao, caudal):
        """Responde à barragem (ação `.responder`).

        Args:
            id_proposta (int): Proposta em análise.
            decisao (str): "aceita", "contraproposta" ou "rejeita".
            caudal (float): O limite do bairro, usado na contraproposta.
        """
        proposta = self.propostas.pop(id_proposta, None)
        if proposta is None or not self.rede.pode_comunicar(self.nome, "barragem"):
            return
        aceita = decisao == "aceita"
        contraproposta = None
        if decisao == "contraproposta":
            contraproposta = {k: v for k, v in proposta.corpo.items() if k != "tipo"}
            contraproposta["caudal"] = caudal
        # o voto leva o thread da proposta, para a barragem o associar à negociação
        self.submit(self.bdi.send(mensagens.criar(
            "barragem",
            mensagens.ACCEPT_PROPOSAL if aceita else mensagens.REJECT_PROPOSAL,
            mensagens.VOTACAO, "voto", thread=proposta.thread,
            aceita=aceita, contraproposta=contraproposta)))
        registo.detalhe(self.nome, f"{'aceitou' if aceita else 'recusou'} o plano "
                                   f"(risco {self.risco_do_bairro}); contraproposta "
                                   f"{contraproposta}")
