"""Agente 1 — Operador da Barragem (existe um só).

A negociação da descarga é uma máquina de estados (FSMBehaviour), uma por
negociação, com os estados do guia (docs/gaia_detalhado.md, secção 9.4):

    PROPOR -> AGUARDAR -> ENCERRAR
                 |
                 +-> REFORMULAR -> PROPOR (outra rodada) ou ENCERRAR

- PROPOR: envia o plano (caudal, atraso, duração) aos três líderes.
- AGUARDAR: recolhe as respostas da rodada. Quem não responde a tempo conta
  como "não". Há maioria? Fim. Senão, e se ainda há rodadas, reformula.
- REFORMULAR: baixa o caudal para a contraproposta mais restritiva dos líderes.
- ENCERRAR: fecha a negociação e submete a proposta final à votação.

A votação é separada da negociação (CoordenadorVotacao, secção 5.2 do guia):
um OneShotBehaviour (`Votacao`) envia a proposta final aos líderes no
protocolo `votacao`, recolhe os votos e aprova com pelo menos 2 em 3. Cada
líder tem um voto por negociação e quem não responde a tempo vota contra.
Só depois a barragem executa a descarga aprovada.

O número máximo de rodadas é MAX_RODADAS (config.py). A validação de segurança
depois do voto e a contingência ficam para a tarefa t09.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from spade.agent import Agent
from spade.behaviour import (FSMBehaviour, OneShotBehaviour, PeriodicBehaviour,
                             State)
from spade.template import Template

import mensagens
import metricas
import registo
from config import (ESPERA_INICIAL, MAX_RODADAS, NIVEL_ALERTA_RESERVATORIO,
                    PASSWORD, PERIODO_CICLO, PERIODO_MONITORIZACAO,
                    TEMPO_ESPERA_VOTOS, jid)
from rede import REDE

# estados da negociação
PROPOR = "PROPOR"
AGUARDAR = "AGUARDAR"
REFORMULAR = "REFORMULAR"
ENCERRAR = "ENCERRAR"


@dataclass
class Negociacao:
    """Estado de uma negociação de descarga em curso.

    Attributes:
        thread (str): Id da negociação, como "desc-001".
        plano (dict): Plano em cima da mesa nesta rodada (caudal, atraso, duração).
        lideres (list): Nomes dos líderes com quem a rede permite falar.
        rodada (int): Rodada atual, a começar em 1.
        respostas (dict): Resposta de cada líder (nome em minúsculas) nesta rodada:
            {"aceita": bool, "contraproposta": dict | None, "sem_resposta": bool}.
        fase (str): "negociando" ou "votando". A barragem só abre outra
            negociação quando esta acaba (`DamOperator.negociacao` volta a None).
    """

    thread: str
    plano: dict
    lideres: list
    rodada: int = 1
    respostas: dict = field(default_factory=dict)
    fase: str = "negociando"

    @property
    def id_proposta(self):
        """Id da proposta desta rodada, como "desc-001-r2"."""
        return f"{self.thread}-r{self.rodada}"


def em_ciclos(ciclos):
    """Escreve uma duração em ciclos e em segundos, como "10 ciclos (20 s)".

    Args:
        ciclos (int): Número de ciclos do ambiente. Cada um dura
            `PERIODO_CICLO` segundos de relógio (config.py).

    Returns:
        str: Texto para o registo do terminal.
    """
    return f"{ciclos} ciclos ({ciclos * PERIODO_CICLO:.0f} s)"


def contar_favoraveis(respostas):
    """Conta as respostas que aceitam a proposta.

    Args:
        respostas (dict): Respostas dos líderes (ver `Negociacao.respostas`).

    Returns:
        int: Número de líderes que aceitaram.
    """
    return sum(1 for r in respostas.values() if r["aceita"])


def ha_maioria(favoraveis, total):
    """Maioria simples: mais de metade (2 em 3 com três líderes).

    Args:
        favoraveis (int): Votos a favor.
        total (int): Número de líderes.

    Returns:
        bool: True se há maioria.
    """
    return favoraveis > total / 2


def reformular(plano, respostas):
    """Cria o plano da rodada seguinte a partir das contrapropostas dos líderes.

    Adota a contraproposta mais restritiva (o menor caudal), porque é a que
    mais líderes conseguem aceitar. Só devolve um plano novo se o caudal baixar.

    Args:
        plano (dict): Plano da rodada que acabou.
        respostas (dict): Respostas dos líderes (ver `Negociacao.respostas`).

    Returns:
        dict | None: O novo plano, ou None se ninguém contrapropôs ou se a
        contraproposta não baixa o caudal (a negociação não pode avançar).
    """
    caudais = [r["contraproposta"]["caudal"] for r in respostas.values()
               if r["contraproposta"]]
    if not caudais:
        return None
    novo = dict(plano, caudal=round(min(caudais), 1))
    if novo["caudal"] >= plano["caudal"]:
        return None
    return novo


def resumo_respostas(respostas):
    """Texto curto com a resposta de cada bairro, como "A:não B:sim C:sem resposta".

    Args:
        respostas (dict): Respostas dos líderes (ver `Negociacao.respostas`).

    Returns:
        str: Uma entrada por líder, pela ordem alfabética.
    """
    def texto(r):
        if r.get("sem_resposta"):
            return "sem resposta"
        return "sim" if r["aceita"] else "não"
    return " ".join(f"{nome[-1].upper()}:{texto(r)}"
                    for nome, r in sorted(respostas.items()))


class Propor(State):
    """PROPOR: envia o plano desta rodada aos líderes."""

    async def run(self):
        n = self.agent.negociacao
        n.respostas = {}
        for lider in n.lideres:
            await self.send(mensagens.criar(
                lider, mensagens.PROPOSE, mensagens.NEGOCIAR_DESCARGA,
                "proposta_descarga", thread=n.thread,
                id_proposta=n.id_proposta, rodada=n.rodada, **n.plano))
        registo.detalhe(self.agent.nome,
                        f"rodada {n.rodada} ({n.id_proposta}): plano {n.plano}")
        if n.rodada == 1:
            # o tempo até à decisão conta desde a primeira proposta
            metricas.proposta(n.plano["caudal"])
        self.set_next_state(AGUARDAR)


class Aguardar(State):
    """AGUARDAR: recolhe as respostas dos líderes e decide o passo seguinte."""

    async def run(self):
        n = self.agent.negociacao
        esperados = [lider.lower() for lider in n.lideres]
        while len(n.respostas) < len(esperados):
            msg = await self.receive(timeout=TEMPO_ESPERA_VOTOS)
            if msg is None:
                break
            r = mensagens.ler(msg)
            if (r is None or r.tipo != "resposta_proposta"
                    or r.remetente not in esperados
                    or r.corpo.get("id_proposta") != n.id_proposta):
                continue        # outra rodada, outro remetente ou lixo
            n.respostas[r.remetente] = {
                "aceita": r.performativa == mensagens.ACCEPT_PROPOSAL,
                "contraproposta": r.corpo.get("contraproposta"),
            }
        for lider in esperados:
            n.respostas.setdefault(lider, {"aceita": False, "contraproposta": None,
                                           "sem_resposta": True})

        favoraveis = contar_favoraveis(n.respostas)
        if ha_maioria(favoraveis, len(esperados)) or n.rodada >= MAX_RODADAS:
            self.set_next_state(ENCERRAR)
        else:
            self.set_next_state(REFORMULAR)


class Reformular(State):
    """REFORMULAR: baixa o caudal para a contraproposta mais restritiva."""

    async def run(self):
        dam = self.agent
        n = dam.negociacao
        novo = reformular(n.plano, n.respostas)
        if novo is None or not dam.validar_plano(novo):
            self.set_next_state(ENCERRAR)       # ninguém contrapropôs, ou não avança
            return
        registo.evento(
            "NEGOCIAÇÃO",
            f"rodada {n.rodada}: caudal {n.plano['caudal']} | "
            f"{resumo_respostas(n.respostas)} -> nova proposta com caudal "
            f"{novo['caudal']}")
        n.plano = novo
        n.rodada += 1
        self.set_next_state(PROPOR)


class Encerrar(State):
    """ENCERRAR: fecha a negociação e submete a proposta final à votação.

    A proposta final é o plano da última rodada, haja ou não maioria nas
    respostas: as respostas da negociação não vinculam, só o voto decide.
    """

    async def run(self):
        dam = self.agent
        n = dam.negociacao
        n.fase = "votando"          # a negociação continua "ocupada" até ao fim do voto
        registo.detalhe(dam.nome, f"negociação {n.thread} encerrada ao fim de "
                                  f"{n.rodada} rodada(s): proposta final {n.plano}")
        dam.add_behaviour(*dam.criar_votacao())


class Votacao(OneShotBehaviour):
    """Papel CoordenadorVotacao: vota a proposta final e executa a descarga.

    Envia a proposta final aos líderes, recolhe os votos e aprova com pelo
    menos 2 em 3 (`ha_maioria`). Regras do guia: um voto por líder em cada
    negociação, e quem não responde a tempo conta como voto contra. Só recebe
    mensagens do protocolo `votacao` desta negociação (template).
    """

    async def run(self):
        dam = self.agent
        n = dam.negociacao
        try:
            votos = await self.recolher_votos(n)
            await self.decidir(n, votos)
        finally:
            dam.negociacao = None       # a barragem pode abrir outra negociação

    async def recolher_votos(self, n):
        """Pede o voto aos líderes e conta as respostas que chegam a tempo.

        Args:
            n (Negociacao): A negociação cuja proposta final se vota.

        Returns:
            dict: Voto de cada líder (nome em minúsculas), como
            {"aceita": bool, "sem_resposta": bool}. Quem não respondeu tem
            "aceita" falso.
        """
        for lider in n.lideres:
            await self.send(mensagens.criar(
                lider, mensagens.PROPOSE, mensagens.VOTACAO, "pedido_voto",
                thread=n.thread, id_proposta=n.id_proposta, **n.plano))
        esperados = [lider.lower() for lider in n.lideres]
        votos = {}
        while len(votos) < len(esperados):
            msg = await self.receive(timeout=TEMPO_ESPERA_VOTOS)
            if msg is None:
                break
            r = mensagens.ler(msg)
            if (r is None or r.tipo != "voto" or r.remetente not in esperados
                    or r.remetente in votos
                    or r.corpo.get("id_proposta") != n.id_proposta):
                continue        # outra negociação, um segundo voto ou lixo
            votos[r.remetente] = {"aceita": r.performativa == mensagens.ACCEPT_PROPOSAL}
        for lider in esperados:
            votos.setdefault(lider, {"aceita": False, "sem_resposta": True})
        return votos

    async def decidir(self, n, votos):
        """Conta os votos e, se a proposta foi aprovada, executa a descarga.

        Args:
            n (Negociacao): A negociação votada.
            votos (dict): Os votos (ver `recolher_votos`).
        """
        dam = self.agent
        total = len(n.lideres)
        favoraveis = contar_favoraveis(votos)
        aprovado = ha_maioria(favoraveis, total)
        plano = n.plano
        metricas.decisao(aprovado, favoraveis, total)
        rodadas = f" | {n.rodada} rodadas" if n.rodada > 1 else ""
        registo.evento(
            "VOTAÇÃO",
            f"caudal {plano['caudal']} (atraso {plano['atraso']}, duração "
            f"{em_ciclos(plano['duracao'])}) | {resumo_respostas(votos)} | "
            f"{favoraveis}/{total} -> "
            + ("aprovado" if aprovado else "rejeitado, nada foi executado")
            + rodadas)
        dam.negociacoes.append({"thread": n.thread, "rodadas": n.rodada,
                                "aprovada": aprovado, "caudal": plano["caudal"]})

        if not aprovado:
            dam.rejeitados += 1
            return
        dam.executar_descarga(plano)
        dam.descargas += 1
        metricas.descarga(plano["caudal"], plano["duracao"])
        registo.evento(
            "DESCARGA",
            f"caudal {plano['caudal']} durante {em_ciclos(plano['duracao'])} "
            f"(reservatório a {dam.nivel_reservatorio:.1f}%)")
        for b in "ABC":
            if dam.rede.pode_comunicar(dam.nome, f"op{b}"):
                await self.send(mensagens.criar(
                    f"op{b}", mensagens.INFORM, mensagens.NEGOCIAR_DESCARGA,
                    "aviso_descarga", thread=n.thread, **plano))


class NegociarDescarga(FSMBehaviour):
    """Uma negociação de descarga, do primeiro plano até ao fim."""

    async def on_end(self):
        # Se um estado falhou, a negociação nunca chegou à votação: liberta a
        # barragem para abrir outra. Se chegou, é a votação que a liberta.
        n = self.agent.negociacao
        if n is not None and n.fase == "negociando":
            self.agent.negociacao = None


class DamOperator(Agent):
    """Agente 1 — Operador da Barragem (existe um só).

    Attributes:
        nome (str): Nome do agente ("barragem").
        negociacao (Negociacao | None): Negociação em curso, se houver.
        negociacoes (list): Resumo das negociações já terminadas.
        descargas (int): Descargas executadas.
        rejeitados (int): Planos rejeitados pelos líderes.
    """

    def __init__(self, nome, ambiente, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.ambiente = ambiente         # mundo simulado (ambiente.py)
        self.caudal_maximo_seguro = 80.0 # limite operacional das comportas
        self.descargas = 0               # descargas executadas (para o resumo final)
        self.rejeitados = 0              # planos rejeitados pelos líderes
        self.negociacao = None           # negociação em curso
        self.negociacoes = []            # negociações terminadas

    class Monitorizar(PeriodicBehaviour):
        """De tempos a tempos: avalia o reservatório e, se for preciso e não
        houver já uma negociação, abre uma negociação com os líderes."""

        async def run(self):
            dam = self.agent
            if dam.negociacao is not None or not dam.avaliar_descarga():
                return

            plano = dam.propor_plano()
            if not dam.validar_plano(plano):
                if plano is not None:
                    metricas.rejeitada_seguranca(f"plano fora dos limites: {plano}")
                return

            lideres = [f"lider{b}" for b in "ABC"
                       if dam.rede.pode_comunicar(dam.nome, f"lider{b}")]
            if not lideres:
                return
            dam.negociacao = Negociacao(thread=mensagens.novo_id("desc"),
                                        plano=plano, lideres=lideres)
            dam.add_behaviour(*dam.criar_negociacao())

    async def setup(self):
        registo.detalhe(self.nome, "agente ativo")
        arranque = datetime.now() + timedelta(seconds=ESPERA_INICIAL)
        # O Monitorizar não recebe mensagens: ~Template() (o complemento do
        # template vazio) não deixa passar nenhuma. As respostas vão para o FSM
        # da negociação e para o behaviour da votação, cada um com o seu template.
        self.add_behaviour(self.Monitorizar(period=PERIODO_MONITORIZACAO,
                                            start_at=arranque), ~Template())

    def criar_negociacao(self):
        """Monta o FSM da negociação em curso e o template que o alimenta.

        O template só deixa passar respostas desta negociação (protocolo
        negociar-descarga e o thread dela), por isso respostas de outras
        negociações nunca chegam aqui.

        Returns:
            tuple: (FSMBehaviour, Template), prontos para `add_behaviour`.
        """
        fsm = NegociarDescarga()
        fsm.add_state(PROPOR, Propor(), initial=True)
        fsm.add_state(AGUARDAR, Aguardar())
        fsm.add_state(REFORMULAR, Reformular())
        fsm.add_state(ENCERRAR, Encerrar())
        fsm.add_transition(PROPOR, AGUARDAR)
        fsm.add_transition(AGUARDAR, REFORMULAR)
        fsm.add_transition(AGUARDAR, ENCERRAR)
        fsm.add_transition(REFORMULAR, PROPOR)
        fsm.add_transition(REFORMULAR, ENCERRAR)
        template = mensagens.template(
            mensagens.NEGOCIAR_DESCARGA, mensagens.ACCEPT_PROPOSAL,
            mensagens.REJECT_PROPOSAL, thread=self.negociacao.thread)
        return fsm, template

    def criar_votacao(self):
        """Monta o behaviour da votação da proposta final e o seu template.

        O template só deixa passar votos (protocolo votacao, performativas
        accept-proposal e reject-proposal) com o thread desta negociação.

        Returns:
            tuple: (Votacao, Template), prontos para `add_behaviour`.
        """
        template = mensagens.template(
            mensagens.VOTACAO, mensagens.ACCEPT_PROPOSAL,
            mensagens.REJECT_PROPOSAL, thread=self.negociacao.thread)
        return Votacao(), template

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
