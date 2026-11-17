"""Agentes 3A, 3B, 3C — Líder comunitário de um bairro (agente BDI).

O líder é um `BDIAgent` (spade_bdi). Divisão de trabalho:

- `lider.asl` (AgentSpeak) decide: crenças sobre o risco, a proposta de
  descarga e o que falta no estoque, desejos e planos.
- Este ficheiro percebe e age: os behaviours do SPADE recebem as mensagens e
  convertem-nas em crenças; as ações `.pedir_mitigacao`, `.responder`,
  `.votar` e `.contratar` enviam as mensagens que resultam das decisões.

Papéis Gaia que o líder desempenha (secção 9.3.1 do modelo):

- RepresentanteBairro: negocia a descarga e vota (com a barragem).
- Comprador: contrata a outro bairro o que falta no estoque
  (`ContractNetComprador`, em agentes/contract_net.py, um FSM por compra).
- Fornecedor: publica ofertas no diretório e responde ao Contract Net dos
  outros bairros (`Vendas`, em agentes/contract_net.py, chamado pelo behaviour
  `FornecedorServicos`).
"""

import unicodedata
from pathlib import Path

from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade_bdi.bdi import BDIAgent

import mensagens
import mercado
import registo
from agentes.contract_net import (Compra, ContractNetComprador, Vendas,
                                  template_comprador)
from config import PASSWORD, PRECO_BASE, jid
from rede import REDE

FICHEIRO_ASL = str(Path(__file__).with_name("lider.asl"))

# respostas do operador a um pedido de mitigação que dizem o que faltou
TIPOS_COM_FALTA = ("mitigacao_recusada", "mitigacao_aceite", "mitigacao_falhou")


def atomo(texto):
    """Converte um texto num átomo do AgentSpeak (sem acentos).

    Args:
        texto (str): Por exemplo "crítico".

    Returns:
        str: Por exemplo "critico".
    """
    sem_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acentos if not unicodedata.combining(c))


def templates_do_lider():
    """Os filtros dos dois behaviours que escutam o líder.

    Qualquer mensagem que chegue ao líder e não encaixe em nenhum destes
    templates fica sem behaviour e o SPADE escreve "No behaviour matched for
    message" no terminal. Por isso, quando um agente passa a enviar uma
    mensagem nova ao líder, este é o sítio onde a receber (e o teste
    `test_lider_bdi` confere a lista).

    Returns:
        tuple: (recebe, fornece). `recebe` serve o `OuvirMensagens`: alertas e
        respostas do operador, respostas do diretório às ofertas, propostas,
        avisos e pedidos de voto da barragem. `fornece` serve o
        `FornecedorServicos`: o Contract Net dos outros bairros e a execução
        de serviços.
    """
    recebe = (mensagens.template(mensagens.ALERTA_RISCO, mensagens.INFORM)
              | mensagens.template(mensagens.PEDIR_MITIGACAO, mensagens.AGREE,
                                   mensagens.REFUSE, mensagens.INFORM,
                                   mensagens.FAILURE)
              | mensagens.template(mensagens.GERIR_OFERTA, mensagens.AGREE,
                                   mensagens.REFUSE)
              | mensagens.template(mensagens.NEGOCIAR_DESCARGA, mensagens.PROPOSE,
                                   mensagens.INFORM)
              | mensagens.template(mensagens.VOTACAO, mensagens.PROPOSE))
    fornece = (mensagens.template(mensagens.CONTRACT_NET, mensagens.CFP,
                                  mensagens.PROPOSE, mensagens.ACCEPT_PROPOSAL,
                                  mensagens.REJECT_PROPOSAL, mensagens.INFORM)
               | mensagens.template(mensagens.EXECUTAR_SERVICO, mensagens.AGREE,
                                    mensagens.INFORM, mensagens.FAILURE))
    return recebe, fornece


class CommunityLeader(BDIAgent):
    """Agentes 3A, 3B, 3C — Líder comunitário de um bairro.

    Attributes:
        nome (str): Nome do agente, como "liderA".
        bairro (str): "A", "B" ou "C".
        rede: Quem pode comunicar com quem (rede.py).
        ambiente (ambiente.Ambiente | None): O mundo simulado. Dá o estoque e
            a moeda do bairro; sem ele o líder não compra nem vende.
        risco_do_bairro (str): Último risco recebido do operador.
        recursos_pedidos (dict): Último pedido de recursos feito ao operador.
        propostas (dict): Propostas de descarga em análise, por id.
        votacoes (dict): Pedidos de voto em análise, por id.
        vendas (Vendas): O papel Fornecedor (Contract Net, lado do vendedor).
        compras (dict): Contratações em curso, por serviço (uma por serviço).
        historico_compras (list): Contratações já terminadas.
        moeda_comprometida (float): Moeda já prometida em contratos que ainda
            não foram pagos.
    """

    def __init__(self, nome, bairro, ambiente=None, password=PASSWORD):
        """Cria o líder de um bairro e carrega o seu `lider.asl` (ainda não o arranca).

        Args:
            nome (str): Nome do agente, que dá o JID (por exemplo "liderA").
            bairro (str): "A", "B" ou "C".
            ambiente (ambiente.Ambiente | None): O mundo simulado.
            password (str): Palavra-passe no servidor XMPP.
        """
        super().__init__(jid(nome), password, FICHEIRO_ASL)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.bairro = bairro
        self.ambiente = ambiente         # mundo simulado (ambiente.py)
        self.risco_do_bairro = "baixo"   # último risco recebido do operador
        self.recursos_pedidos = {}       # bombas, barreiras, equipa...
        self.propostas = {}              # id -> proposta da barragem
        self.votacoes = {}               # id -> pedido de voto da barragem
        self.vendas = Vendas(self)       # papel Fornecedor
        self.compras = {}                # servico -> Compra em curso
        self.historico_compras = []      # Compras terminadas
        self.moeda_comprometida = 0.0
        self._seq_propostas = 0
        self._seq_faltas = 0
        self._seq_compras = 0
        self._ofertas_publicadas = False # as ofertas só se publicam uma vez

    @property
    def estado(self):
        """O bairro no ambiente: nível, estoque, reservas e moeda."""
        return self.ambiente.bairros[self.bairro]

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
        actions.add_procedure(
            ".votar", (int, None),
            lambda id_voto, voto: self.votar(id_voto, str(voto)))
        actions.add_procedure(
            ".contratar", (None, int),
            lambda recurso, quantidade: self.contratar(str(recurso), int(quantidade)))

    class OuvirMensagens(CyclicBehaviour):
        """Recebe alertas do operador do bairro, as respostas dele aos pedidos
        de mitigação e as propostas da barragem, e transforma-os em crenças
        do agente BDI."""

        async def run(self):
            """Espera uma mensagem e converte-a numa crença do `lider.asl`
            (`risco`, `falta`, `proposta`, `votacao` ou `contingencia`), que
            dispara os planos de decisão."""
            lider = self.agent
            msg = mensagens.ler(await self.receive(timeout=1))
            if msg is None:
                return

            if msg.tipo == "alerta_risco":
                lider.risco_do_bairro = msg.corpo["risco"]
                lider.bdi.set_belief("risco", atomo(msg.corpo["risco"]))

            elif msg.protocolo == mensagens.PEDIR_MITIGACAO:
                # o operador diz o que não tinha em estoque (AGREE e INFORM
                # repetem a mesma falta, por isso só conta a primeira resposta)
                if msg.tipo in TIPOS_COM_FALTA:
                    lider.registar_falta(msg.corpo.get("falta") or {})

            elif msg.protocolo == mensagens.GERIR_OFERTA:
                # resposta do diretório à publicação das ofertas. O diretório já
                # mostra o evento OFERTA; aqui só se avisa se as recusou
                if msg.performativa == mensagens.REFUSE:
                    registo.evento("OFERTA", f"bairro {lider.bairro}: o diretório "
                                             f"recusou as ofertas "
                                             f"({msg.corpo.get('motivo')})")
                else:
                    registo.detalhe(lider.nome, "o diretório registou as ofertas")

            elif msg.tipo == "proposta_descarga":
                if not lider.rede.pode_comunicar(lider.nome, "barragem"):
                    return
                lider._seq_propostas += 1
                id_proposta = lider._seq_propostas
                lider.propostas[id_proposta] = msg      # guarda o thread para responder
                lider.bdi.set_belief("proposta", id_proposta,
                                     float(msg.corpo["caudal"]))

            elif msg.tipo == "pedido_voto":
                if not lider.rede.pode_comunicar(lider.nome, "barragem"):
                    return
                lider._seq_propostas += 1
                id_voto = lider._seq_propostas
                lider.votacoes[id_voto] = msg           # guarda o thread para votar
                lider.bdi.set_belief("votacao", id_voto, float(msg.corpo["caudal"]))

            elif msg.tipo == "aviso_contingencia":
                # a barragem decidiu sozinha: o líder fica a saber (crença) e o
                # plano do .asl regista-o
                lider.bdi.set_belief("contingencia", float(msg.corpo["caudal"]))

    class FornecedorServicos(CyclicBehaviour):
        """Papel Fornecedor: responde ao Contract Net dos outros bairros e
        às respostas do operador sobre os serviços executados."""

        async def run(self):
            """Espera uma mensagem e entrega-a ao `Vendas`, que devolve as
            mensagens a enviar (pode não haver nenhuma)."""
            lider = self.agent
            msg = mensagens.ler(await self.receive(timeout=1))
            if msg is None:
                return
            for resposta in lider.vendas.tratar(msg):
                await self.send(resposta)

    class PublicarOfertas(OneShotBehaviour):
        """Publica no diretório as ofertas do bairro, uma vez, no arranque."""

        async def run(self):
            """Envia ao diretório o que o bairro pode vender (GerirOferta)."""
            for oferta in self.agent.mensagens_ofertas():
                await self.send(oferta)

    async def setup(self):
        """Arranca os behaviours do líder.

        O template do `OuvirMensagens` deixa passar só os alertas dos
        operadores, as respostas deles aos pedidos de mitigação, as propostas
        e os avisos de contingência da barragem (negociação) e os pedidos de
        voto. O `FornecedorServicos` recebe as mensagens do Contract Net e da
        execução de serviços; as respostas ao nosso Contract Net de comprador
        vão para o FSM de cada compra (ver `contratar`).
        """
        registo.detalhe(self.nome, f"agente BDI ativo (bairro {self.bairro})")
        recebe, fornece = templates_do_lider()
        self.add_behaviour(self.OuvirMensagens(), recebe)
        self.add_behaviour(self.FornecedorServicos(), fornece)
        self.add_behaviour(self.PublicarOfertas())

    # ---- mercado: ofertas, faltas e contratação -----------------------------

    def mensagens_ofertas(self):
        """Mensagem ao diretório com as ofertas do bairro, uma só vez.

        Publica todos os serviços com excedente (regra 7) numa única mensagem
        e não volta a publicar. As ofertas não são atualizadas depois: se o
        estoque acabar ou o risco subir, o fornecedor recusa o CFP
        (`Vendas.cfp` confere o estoque real), o que custa menos mensagens do
        que manter o diretório em dia.

        Returns:
            list: Uma mensagem SPADE (REQUEST "publicar_ofertas"), ou lista
            vazia se já publicou, se não há nada para oferecer ou se o líder
            não tem ambiente.
        """
        if (self.ambiente is None or self._ofertas_publicadas
                or not self.rede.pode_comunicar(self.nome, "diretorio")):
            return []
        self._ofertas_publicadas = True
        ofertas = []
        for servico in PRECO_BASE:
            quantidade = mercado.excedente(self.estado, servico, self.risco_do_bairro)
            if quantidade > 0:
                ofertas.append({"servico": servico, "quantidade": quantidade,
                                "preco": mercado.preco_pedido_inicial(servico)})
        if not ofertas:
            return []
        return [mensagens.criar("diretorio", mensagens.REQUEST, mensagens.GERIR_OFERTA,
                                "publicar_ofertas", ofertas=ofertas)]

    def registar_falta(self, falta):
        """Transforma o que faltou no estoque em crenças `falta(Id, Recurso, Qtd)`.

        Cada falta leva um id novo, para o mesmo recurso em falta duas vezes
        voltar a disparar o plano do `lider.asl` que decide se contrata.

        Args:
            falta (dict): Quantidade em falta por recurso, como {"bombas": 2}.
        """
        for recurso, quantidade in falta.items():
            if int(quantidade) <= 0:
                continue
            self._seq_faltas += 1
            self.bdi.set_belief("falta", self._seq_faltas, str(recurso), int(quantidade))

    def contratar(self, recurso, quantidade):
        """Começa um Contract Net de comprador para o que falta (ação `.contratar`).

        Só há uma contratação em curso por serviço. O FSM recebe apenas as
        mensagens do seu thread (`cn-<bairro>-<n>`).

        Args:
            recurso (str): Serviço a contratar, como "bombas".
            quantidade (int): Unidades que faltam.
        """
        if self.ambiente is None or quantidade <= 0:
            return
        if recurso in self.compras:
            registo.detalhe(self.nome, f"já está a contratar {recurso}")
            return
        self._seq_compras += 1
        thread = f"cn-{self.bairro}-{self._seq_compras:03d}"
        self.compras[recurso] = Compra(thread, recurso, int(quantidade))
        registo.detalhe(self.nome, f"{thread}: vai contratar {recurso} x{quantidade}")
        self.add_behaviour(ContractNetComprador(recurso), template_comprador(thread))

    # ---- barragem: negociação e voto ----------------------------------------

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
            # o plano da barragem, com o caudal que o bairro aguenta
            contraproposta = {c: proposta.corpo[c] for c in ("atraso", "duracao")
                              if c in proposta.corpo}
            contraproposta["caudal"] = caudal
        # a resposta leva o thread e o id da proposta, para a barragem a associar
        # à negociação e à rodada certas
        self.submit(self.bdi.send(mensagens.criar(
            "barragem",
            mensagens.ACCEPT_PROPOSAL if aceita else mensagens.REJECT_PROPOSAL,
            mensagens.NEGOCIAR_DESCARGA, "resposta_proposta",
            thread=proposta.thread, id_proposta=proposta.corpo.get("id_proposta"),
            rodada=proposta.corpo.get("rodada"),
            aceita=aceita, contraproposta=contraproposta)))
        registo.detalhe(self.nome, f"{'aceitou' if aceita else 'recusou'} o plano "
                                   f"(risco {self.risco_do_bairro}); contraproposta "
                                   f"{contraproposta}")

    def votar(self, id_voto, voto):
        """Vota a proposta final da barragem (ação `.votar`).

        Num voto só há sim ou não: não se negoceia.

        Args:
            id_voto (int): Pedido de voto em análise.
            voto (str): "sim" ou "nao".
        """
        pedido = self.votacoes.pop(id_voto, None)
        if pedido is None or not self.rede.pode_comunicar(self.nome, "barragem"):
            return
        aceita = voto == "sim"
        # o voto leva o thread e o id da proposta votada: um voto por negociação
        self.submit(self.bdi.send(mensagens.criar(
            "barragem",
            mensagens.ACCEPT_PROPOSAL if aceita else mensagens.REJECT_PROPOSAL,
            mensagens.VOTACAO, "voto", thread=pedido.thread,
            id_proposta=pedido.corpo.get("id_proposta"), aceita=aceita)))
        registo.detalhe(self.nome, f"votou {'sim' if aceita else 'não'} "
                                   f"(risco {self.risco_do_bairro})")
