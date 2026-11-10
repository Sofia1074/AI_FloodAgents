"""Agentes 3A, 3B, 3C — Líder comunitário de um bairro."""

import json

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

import registo
from config import CAUDAL_ACEITE, PASSWORD, RECURSOS_POR_RISCO, jid
from rede import REDE


class CommunityLeader(Agent):
    """Agentes 3A, 3B, 3C — Líder comunitário de um bairro."""

    def __init__(self, nome, bairro, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.bairro = bairro
        self.risco_do_bairro = "baixo"   # último risco recebido do operador
        self.recursos_pedidos = {}       # bombas, barreiras, equipa...

    class OuvirMensagens(CyclicBehaviour):
        """Recebe alertas do operador do bairro e propostas da barragem."""

        async def run(self):
            lider = self.agent
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            origem = msg.sender.user
            conteudo = json.loads(msg.body)
            performative = msg.get_metadata("performative")

            if origem.startswith("op") and performative == "inform":
                # alerta do operador -> pede recursos de volta, se for preciso
                pedidos = lider.receber_alerta(conteudo)
                destino = f"op{lider.bairro}"
                if pedidos and lider.rede.pode_comunicar(lider.nome, destino):
                    pedido = Message(to=jid(destino))
                    pedido.set_metadata("performative", "request")
                    pedido.body = json.dumps({"recursos": pedidos})
                    await self.send(pedido)
                    registo.detalhe(lider.nome, f"risco {lider.risco_do_bairro}: "
                                    f"pediu recursos {pedidos}")

            elif origem == "barragem" and performative == "propose":
                # proposta da barragem -> vota (e, se recusar, contrapropõe)
                if not lider.rede.pode_comunicar(lider.nome, "barragem"):
                    return
                resposta = lider.propor(conteudo)
                voto = Message(to=jid("barragem"))
                voto.set_metadata(
                    "performative",
                    "accept-proposal" if resposta["aceita"] else "reject-proposal")
                voto.body = json.dumps(resposta)
                await self.send(voto)
                registo.detalhe(
                    lider.nome,
                    f"{'aceitou' if resposta['aceita'] else 'recusou'} o plano "
                    f"(risco {lider.risco_do_bairro}); contraproposta "
                    f"{resposta['contraproposta']}")

    async def setup(self):
        registo.detalhe(self.nome, f"agente ativo (bairro {self.bairro})")
        self.add_behaviour(self.OuvirMensagens())

    def receber_alerta(self, alerta):
        """Interpreta o alerta enviado pelo operador do bairro.
        Guarda o risco e decide os recursos a pedir (devolve-os)."""
        self.risco_do_bairro = alerta["risco"]
        self.recursos_pedidos = dict(RECURSOS_POR_RISCO[self.risco_do_bairro])
        return self.recursos_pedidos

    def propor(self, plano_da_barragem):
        """Responde à barragem com condições ou uma contraproposta.
        Se aceita, devolve só o voto. Se recusa, propõe o caudal máximo que o
        bairro aguenta (ou nenhuma contraproposta se não aguenta descarga)."""
        if self.votar(plano_da_barragem):
            return {"aceita": True, "contraproposta": None}

        limite = CAUDAL_ACEITE[self.risco_do_bairro]
        contraproposta = None
        if limite > 0:
            contraproposta = dict(plano_da_barragem, caudal=limite)
        return {"aceita": False, "contraproposta": contraproposta}

    def votar(self, plano):
        """Decide se aprova ou rejeita um plano:
        aprova se o caudal couber no que o risco do bairro permite."""
        return plano["caudal"] <= CAUDAL_ACEITE[self.risco_do_bairro]
