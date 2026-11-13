"""Agentes 2A, 2B, 2C — Operador de um bairro."""

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour

import mensagens
import metricas
import registo
from config import CAPACIDADE_TANQUE, PASSWORD, PERIODO_MEDICAO, jid
from rede import REDE
from risco import classificar_risco


class NeighbourhoodOperator(Agent):
    """Agentes 2A, 2B, 2C — Operador de um bairro.

    Attributes:
        nome (str): Nome do agente, como "opA".
        bairro (str): "A", "B" ou "C".
        ambiente (Ambiente): O mundo simulado, de onde lê o nível de água.
        tanque_livre (float): Capacidade de retenção ainda livre.
        risco (str): "baixo", "moderado", "elevado" ou "crítico".
        motivos (list): Agravantes do risco atual (ver risco.py).
        ultimo_risco_enviado (str | None): Último risco que avisou ao líder.
    """

    def __init__(self, nome, bairro, ambiente, password=PASSWORD):
        """Cria o operador de um bairro (ainda não o arranca).

        Args:
            nome (str): Nome do agente, que dá o JID (por exemplo "opA").
            bairro (str): "A", "B" ou "C".
            ambiente (Ambiente): O mundo simulado que o operador lê e altera.
            password (str): Palavra-passe no servidor XMPP.
        """
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.bairro = bairro             # "A", "B" ou "C"
        self.ambiente = ambiente         # mundo simulado (ambiente.py)
        self.tanque_livre = CAPACIDADE_TANQUE   # capacidade de retenção disponível
        self.risco = "baixo"             # baixo, moderado, elevado ou crítico
        self.motivos = []                # agravantes do risco (ver risco.py)
        self.ultimo_risco_enviado = None # para só alertar quando há novidade
        self.subida_rapida_avisada = False

    class Monitorizar(PeriodicBehaviour):
        """De tempos a tempos: mede, avalia o risco e alerta o líder."""

        async def run(self):
            """Uma medição: lê o bairro, avalia o risco e, se o risco mudou ou
            começou uma subida rápida, envia o alerta ao líder (só então)."""
            op = self.agent
            op.medir()
            op.avaliar_risco()

            # só alerta quando há novidade: o risco mudou desde o último
            # alerta, ou começou uma subida rápida (secção 3 do guia)
            subida_rapida = "subida rápida" in op.motivos
            nova_subida = subida_rapida and not op.subida_rapida_avisada
            op.subida_rapida_avisada = subida_rapida
            if op.risco == op.ultimo_risco_enviado and not nova_subida:
                return
            lider = f"lider{op.bairro}"
            if not op.rede.pode_comunicar(op.nome, lider):
                return

            await self.send(mensagens.criar(
                lider, mensagens.INFORM, mensagens.ALERTA_RISCO, "alerta_risco",
                **op.alertar_lider()))
            anterior = op.ultimo_risco_enviado
            op.ultimo_risco_enviado = op.risco
            metricas.alerta(op.bairro, op.risco)
            motivos = f", {', '.join(op.motivos)}" if op.motivos else ""
            dados = (f"(nível {op.nivel_agua:.1f}, a subir "
                     f"{op.velocidade_subida:+.1f}/ciclo{motivos})")
            if anterior is None and op.risco == "baixo" and not op.motivos:
                registo.detalhe(op.nome, "primeira leitura: risco baixo")
            elif anterior is None:
                registo.evento("ALERTA", f"bairro {op.bairro}: risco {op.risco} {dados}")
            elif anterior == op.risco:
                registo.evento("ALERTA", f"bairro {op.bairro}: subida rápida, risco "
                                         f"continua {op.risco} {dados}")
            else:
                registo.evento("ALERTA", f"bairro {op.bairro}: {anterior} -> "
                                         f"{op.risco} {dados}")

    class OuvirMensagens(CyclicBehaviour):
        """Recebe: pedidos de recursos do líder e avisos de descarga da barragem."""

        async def run(self):
            """Espera uma mensagem: ativa a mitigação pedida pelo líder ou
            regista o aviso de descarga da barragem."""
            op = self.agent
            msg = mensagens.ler(await self.receive(timeout=1))
            if msg is None:
                return
            conteudo = msg.corpo

            if msg.tipo == "pedido_mitigacao":
                op.ativar_mitigacao(conteudo["recursos"])
                metricas.mitigacao(op.bairro, conteudo["recursos"])
                registo.evento(
                    "MITIGAÇÃO",
                    f"bairro {op.bairro}: {conteudo['recursos']} ativados "
                    f"(nível {op.nivel_agua:.1f})")
            elif msg.tipo == "aviso_descarga":
                # só um aviso: a água da descarga chega pelo ambiente
                registo.detalhe(op.nome, f"aviso de descarga (caudal "
                                f"{conteudo['caudal']}, duração {conteudo['duracao']})")

    async def setup(self):
        """Arranca o behaviour que escuta o líder e a barragem. A monitorização
        só começa em `comecar()`, quando todos os agentes estão ativos."""
        registo.detalhe(self.nome, f"agente ativo (bairro {self.bairro})")
        # a monitorização só arranca em comecar(), quando todos os agentes
        # estiverem ativos (ver comecar)
        # só recebe pedidos de mitigação do líder e avisos de descarga da barragem
        pedidos = (mensagens.template(mensagens.PEDIR_MITIGACAO, mensagens.REQUEST)
                   | mensagens.template(mensagens.NEGOCIAR_DESCARGA, mensagens.INFORM))
        self.add_behaviour(self.OuvirMensagens(), pedidos)

    def comecar(self):
        """Arranca a monitorização do bairro.

        Chamado pelo `main` depois de **todos** os agentes estarem ativos.
        Se o operador medisse logo no arranque, o primeiro alerta podia sair
        antes de o líder estar ligado ao servidor e perder-se (e o operador
        só volta a alertar quando o risco muda). Assim o resultado não depende
        da ordem em que os agentes arrancam.
        """
        self.add_behaviour(self.Monitorizar(period=PERIODO_MEDICAO))

    @property
    def nivel_agua(self):
        """Nível de água do bairro, lido do ambiente (sensor simulado)."""
        return self.ambiente.bairros[self.bairro].nivel

    @property
    def velocidade_subida(self):
        """Quanto o nível subiu no último ciclo do ambiente."""
        return self.ambiente.bairros[self.bairro].velocidade

    def medir(self):
        """Lê os sensores do bairro.
        O nível de água vem do ambiente; aqui calcula-se o que se deduz
        dele: a capacidade de retenção livre.

        Returns:
            tuple: (nível de água, capacidade de retenção livre).
        """
        self.tanque_livre = max(0.0, CAPACIDADE_TANQUE - self.nivel_agua)
        return self.nivel_agua, self.tanque_livre

    def avaliar_risco(self):
        """Calcula o nível de risco a partir das medições: nível, velocidade
        de subida, chuva e capacidade de drenagem (regras em risco.py).
        Guarda os agravantes em `self.motivos`.

        Returns:
            str: "baixo", "moderado", "elevado" ou "crítico".
        """
        b = self.ambiente.bairros[self.bairro]
        self.risco, self.motivos = classificar_risco(
            nivel=b.nivel,
            velocidade=b.velocidade,
            entrada_chuva=b.entrada_chuva(self.ambiente.chuva_ultimo_ciclo),
            drenagem=b.drenagem_natural(),
        )
        return self.risco

    def alertar_lider(self):
        """Prepara o alerta com o risco e os dados, para enviar ao líder
        do bairro (o envio é feito pelo behaviour Monitorizar).

        Returns:
            dict: Bairro, risco, nível de água, velocidade de subida, motivos
            e capacidade de retenção livre.
        """
        return {
            "bairro": self.bairro,
            "risco": self.risco,
            "nivel_agua": self.nivel_agua,
            "velocidade_subida": self.velocidade_subida,
            "motivos": self.motivos,
            "tanque_livre": self.tanque_livre,
        }

    def ativar_mitigacao(self, recursos):
        """Liga bombas, barreiras ou equipas no bairro.
        O efeito acontece no ambiente ao longo dos ciclos seguintes
        (ver EFEITO_RECURSO em config.py).

        Args:
            recursos (dict): Quantidade por recurso, como {"bombas": 2}.
        """
        self.ambiente.aplicar_mitigacao(self.bairro, recursos)
