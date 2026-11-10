"""Agentes 2A, 2B, 2C — Operador de um bairro."""

import json

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message

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

            # só alerta se o risco não for baixo ou se mudou desde o último alerta
            if op.risco == "baixo" and op.risco == op.ultimo_risco_enviado:
                return
            lider = f"lider{op.bairro}"
            if not op.rede.pode_comunicar(op.nome, lider):
                return

            alerta = op.alertar_lider()
            msg = Message(to=jid(lider))
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps(alerta)
            await self.send(msg)
            op.ultimo_risco_enviado = op.risco
            print(f"[{op.nome}] alerta enviado: risco {op.risco} "
                  f"(nível {op.nivel_agua:.1f})", flush=True)

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
                op.ativar_mitigacao(conteudo["recursos"])
                print(f"[{op.nome}] mitigação ativada {conteudo['recursos']} "
                      f"-> nível {op.nivel_agua:.1f}", flush=True)
            elif origem == "barragem" and performative == "inform":
                # a água libertada pela barragem chega ao bairro
                op.nivel_agua = min(CAPACIDADE_TANQUE,
                                    op.nivel_agua + conteudo["caudal"] * FATOR_CHEIA)
                print(f"[{op.nome}] descarga a chegar (caudal {conteudo['caudal']}) "
                      f"-> nível {op.nivel_agua:.1f}", flush=True)

    async def setup(self):
        print(f"[{self.nome}] agente ativo (bairro {self.bairro})", flush=True)
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
