"""Agente 1 — Operador da Barragem (existe um só)."""

import json

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message

from config import (CAPACIDADE_RESERVATORIO, NIVEL_ALERTA_RESERVATORIO,
                    PASSWORD, PERIODO_MONITORIZACAO, TEMPO_ESPERA_VOTOS, jid)
from rede import REDE


class DamOperator(Agent):
    """Agente 1 — Operador da Barragem (existe um só)."""

    def __init__(self, nome, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.nivel_reservatorio = 0.0    # % de enchimento do reservatório
        self.caudal_descarga = 0.0       # caudal que está a ser libertado
        self.caudal_maximo_seguro = 80.0 # limite operacional das comportas

    class Monitorizar(PeriodicBehaviour):
        """De tempos a tempos: avalia o reservatório e, se for preciso,
        propõe o plano aos líderes, conta os votos e executa a descarga."""

        async def run(self):
            dam = self.agent
            if not dam.avaliar_descarga():
                return

            plano = dam.propor_plano()
            if not dam.validar_plano(plano):
                return

            # 1) propor o plano aos líderes com quem a rede permite falar
            lideres = [f"lider{b}" for b in "ABC"
                       if dam.rede.pode_comunicar(dam.nome, f"lider{b}")]
            for lider in lideres:
                msg = Message(to=jid(lider))
                msg.set_metadata("performative", "propose")
                msg.body = json.dumps(plano)
                await self.send(msg)
            print(f"[{dam.nome}] plano proposto: {plano}", flush=True)

            # 2) recolher os votos (quem não responde a tempo conta como "não")
            votos = {}
            while len(votos) < len(lideres):
                resposta = await self.receive(timeout=TEMPO_ESPERA_VOTOS)
                if resposta is None:
                    break
                aceitou = resposta.get_metadata("performative") == "accept-proposal"
                votos[resposta.sender.user] = aceitou
            print(f"[{dam.nome}] votos: {votos}", flush=True)

            # 3) maioria aprova -> executa e informa os operadores de bairro
            if sum(votos.values()) > len(lideres) / 2:
                dam.executar_descarga(plano)
                print(f"[{dam.nome}] descarga executada, reservatório a "
                      f"{dam.nivel_reservatorio:.1f}%", flush=True)
                for b in "ABC":
                    if dam.rede.pode_comunicar(dam.nome, f"op{b}"):
                        info = Message(to=jid(f"op{b}"))
                        info.set_metadata("performative", "inform")
                        info.body = json.dumps(plano)
                        await self.send(info)
            else:
                print(f"[{dam.nome}] plano rejeitado, nada foi executado", flush=True)

    async def setup(self):
        print(f"[{self.nome}] agente ativo", flush=True)
        self.add_behaviour(self.Monitorizar(period=PERIODO_MONITORIZACAO))

    def avaliar_descarga(self):
        """Decide se é preciso fazer uma descarga.
        Há descarga quando o reservatório passa o nível de alerta."""
        return self.nivel_reservatorio > NIVEL_ALERTA_RESERVATORIO

    def propor_plano(self):
        """Cria um plano de descarga (caudal, atraso, duração).
        O plano é um dicionário. Quanto mais cheio o reservatório, maior o
        caudal proposto (nunca acima do máximo seguro). Sem necessidade de
        descarga devolve None."""
        if not self.avaliar_descarga():
            return None

        # fração do "espaço de risco" já ocupada: 0.0 no nível de alerta, 1.0 a 100%
        excesso = (self.nivel_reservatorio - NIVEL_ALERTA_RESERVATORIO) / (
            100.0 - NIVEL_ALERTA_RESERVATORIO)
        excesso = min(excesso, 1.0)

        return {
            "caudal": round(self.caudal_maximo_seguro * excesso, 1),
            "atraso": 0,       # passos de simulação até começar
            "duracao": 10,     # passos de simulação a descarregar
        }

    def validar_plano(self, plano):
        """Verifica se um plano respeita os limites de segurança."""
        if plano is None:
            return False
        return (0 < plano["caudal"] <= self.caudal_maximo_seguro
                and plano["atraso"] >= 0
                and plano["duracao"] > 0)

    def executar_descarga(self, plano):
        """Abre as comportas segundo um plano já validado.
        Regista o caudal e baixa o nível do reservatório pelo volume
        libertado (caudal x duração)."""
        self.caudal_descarga = plano["caudal"]
        volume = plano["caudal"] * plano["duracao"]
        self.nivel_reservatorio = max(
            0.0, self.nivel_reservatorio - 100.0 * volume / CAPACIDADE_RESERVATORIO)
