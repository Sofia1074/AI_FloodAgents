"""Agente 1 — Operador da Barragem (existe um só)."""

import json
from datetime import datetime, timedelta

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message

import registo
from config import (ESPERA_INICIAL, NIVEL_ALERTA_RESERVATORIO, PASSWORD,
                    PERIODO_MONITORIZACAO, TEMPO_ESPERA_VOTOS, jid)
from rede import REDE


class DamOperator(Agent):
    """Agente 1 — Operador da Barragem (existe um só)."""

    def __init__(self, nome, ambiente, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.ambiente = ambiente         # mundo simulado (ambiente.py)
        self.caudal_maximo_seguro = 80.0 # limite operacional das comportas
        self.descargas = 0               # descargas executadas (para o resumo final)
        self.rejeitados = 0              # planos rejeitados pelos líderes

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
            registo.detalhe(dam.nome, f"plano proposto: {plano}")

            # 2) recolher os votos (quem não responde a tempo conta como "não")
            votos = {}
            while len(votos) < len(lideres):
                resposta = await self.receive(timeout=TEMPO_ESPERA_VOTOS)
                if resposta is None:
                    break
                aceitou = resposta.get_metadata("performative") == "accept-proposal"
                votos[resposta.sender.user] = aceitou

            favoraveis = sum(votos.values())
            aprovado = favoraveis > len(lideres) / 2
            por_bairro = " ".join(
                f"{l[-1]}:" + ("sem resposta" if l.lower() not in votos else
                               "sim" if votos[l.lower()] else "não")
                for l in lideres)
            registo.evento(
                "VOTAÇÃO",
                f"caudal {plano['caudal']} (atraso {plano['atraso']}, duração "
                f"{plano['duracao']}) | {por_bairro} | {favoraveis}/{len(lideres)} -> "
                + ("aprovado" if aprovado else "rejeitado, nada foi executado"))

            # 3) maioria aprova -> executa e informa os operadores de bairro
            if aprovado:
                dam.executar_descarga(plano)
                dam.descargas += 1
                registo.evento(
                    "DESCARGA",
                    f"caudal {plano['caudal']} durante {plano['duracao']} ciclos "
                    f"(reservatório a {dam.nivel_reservatorio:.1f}%)")
                for b in "ABC":
                    if dam.rede.pode_comunicar(dam.nome, f"op{b}"):
                        info = Message(to=jid(f"op{b}"))
                        info.set_metadata("performative", "inform")
                        info.body = json.dumps(plano)
                        await self.send(info)
            else:
                dam.rejeitados += 1

    async def setup(self):
        registo.detalhe(self.nome, "agente ativo")
        arranque = datetime.now() + timedelta(seconds=ESPERA_INICIAL)
        self.add_behaviour(self.Monitorizar(period=PERIODO_MONITORIZACAO,
                                            start_at=arranque))

    @property
    def nivel_reservatorio(self):
        """% de enchimento do reservatório, lido do ambiente."""
        return self.ambiente.nivel_reservatorio

    @property
    def caudal_descarga(self):
        """Caudal que está a ser libertado agora."""
        return self.ambiente.caudal_saida

    def avaliar_descarga(self):
        """Decide se é preciso fazer uma descarga.
        Há descarga quando o reservatório passa o nível de alerta e não há
        já uma descarga marcada ou a decorrer."""
        return (self.nivel_reservatorio > NIVEL_ALERTA_RESERVATORIO
                and not self.ambiente.descarga_ativa())

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
        O ambiente liberta o caudal durante os ciclos do plano; o nível do
        reservatório desce aos poucos."""
        self.ambiente.iniciar_descarga(plano["caudal"], plano["duracao"],
                                       plano["atraso"])
