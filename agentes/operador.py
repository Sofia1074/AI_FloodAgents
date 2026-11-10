"""Agentes 2A, 2B, 2C — Operador de um bairro."""

import json

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message

import registo
from config import (CAPACIDADE_TANQUE, EFEITO_RECURSO, FATOR_CHEIA,
                    LIMITES_RISCO, PASSWORD, PERIODO_MEDICAO, jid)
from rede import REDE


class NeighbourhoodOperator(Agent):
    """Agentes 2A, 2B, 2C — Operador de um bairro."""

    def __init__(self, nome, bairro, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.bairro = bairro             # "A", "B" ou "C"
        self.nivel_agua = 0.0            # nível da água no bairro
        self.tanque_livre = CAPACIDADE_TANQUE   # capacidade de retenção disponível
        self.risco = "baixo"             # baixo, moderado, elevado ou crítico
        self.ultimo_risco_enviado = None # para só alertar quando há novidade

    class Monitorizar(PeriodicBehaviour):
        """De tempos a tempos: mede, avalia o risco e alerta o líder."""

        async def run(self):
            op = self.agent
            op.medir()
            op.avaliar_risco()

            # só alerta quando há novidade: o risco mudou desde o último alerta
            if op.risco == op.ultimo_risco_enviado:
                return
            lider = f"lider{op.bairro}"
            if not op.rede.pode_comunicar(op.nome, lider):
                return

            alerta = op.alertar_lider()
            msg = Message(to=jid(lider))
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps(alerta)
            await self.send(msg)
            anterior = op.ultimo_risco_enviado
            op.ultimo_risco_enviado = op.risco
            if anterior is None and op.risco == "baixo":
                registo.detalhe(op.nome, "primeira leitura: risco baixo")
            else:
                registo.evento(
                    "ALERTA",
                    f"bairro {op.bairro}: {anterior or 'baixo'} -> {op.risco} "
                    f"(nível {op.nivel_agua:.1f})")

    class OuvirMensagens(CyclicBehaviour):
        """Recebe: pedidos de recursos do líder e avisos de descarga da barragem."""

        async def run(self):
            op = self.agent
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            origem = msg.sender.user
            conteudo = json.loads(msg.body)
            performative = msg.get_metadata("performative")

            if origem.startswith("lider") and performative == "request":
                antes = op.nivel_agua
                op.ativar_mitigacao(conteudo["recursos"])
                registo.evento(
                    "MITIGAÇÃO",
                    f"bairro {op.bairro}: {conteudo['recursos']} -> nível "
                    f"{antes:.1f} -> {op.nivel_agua:.1f}")
            elif origem == "barragem" and performative == "inform":
                # a água libertada pela barragem chega ao bairro
                antes = op.nivel_agua
                op.nivel_agua = min(CAPACIDADE_TANQUE,
                                    op.nivel_agua + conteudo["caudal"] * FATOR_CHEIA)
                registo.detalhe(op.nome, f"descarga a chegar (caudal "
                                f"{conteudo['caudal']}): nível {antes:.1f} -> "
                                f"{op.nivel_agua:.1f}")

    async def setup(self):
        registo.detalhe(self.nome, f"agente ativo (bairro {self.bairro})")
        self.add_behaviour(self.Monitorizar(period=PERIODO_MEDICAO))
        self.add_behaviour(self.OuvirMensagens())

    def medir(self):
        """Lê os sensores do bairro.
        O nível de água é atualizado de fora (avisos da barragem, mitigação);
        aqui calcula-se o que se deduz dele: a capacidade de retenção livre."""
        self.tanque_livre = max(0.0, CAPACIDADE_TANQUE - self.nivel_agua)
        return self.nivel_agua, self.tanque_livre

    def avaliar_risco(self):
        """Calcula o nível de risco a partir das medições."""
        self.risco = "crítico"
        for limite, risco in LIMITES_RISCO:
            if self.nivel_agua < limite:
                self.risco = risco
                break
        return self.risco

    def alertar_lider(self):
        """Prepara o alerta com o risco e os dados, para enviar ao líder
        do bairro (o envio é feito pelo behaviour Monitorizar)."""
        return {
            "bairro": self.bairro,
            "risco": self.risco,
            "nivel_agua": self.nivel_agua,
            "tanque_livre": self.tanque_livre,
        }

    def ativar_mitigacao(self, recursos):
        """Liga bombas, barreiras ou equipas no bairro.
        Cada recurso baixa o nível de água conforme o seu efeito."""
        reducao = sum(EFEITO_RECURSO.get(nome, 0.0) * qtd
                      for nome, qtd in recursos.items())
        self.nivel_agua = max(0.0, self.nivel_agua - reducao)
        self.medir()
