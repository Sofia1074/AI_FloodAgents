"""Contratação de serviços entre bairros: FIPA Contract Net (secção 5.3 do guia).

Os dois lados vivem no agente líder (agentes/lider.py), porque um bairro pode
comprar num momento e vender noutro (papéis Comprador e Fornecedor).

Comprador: um FSMBehaviour por contratação (`ContractNetComprador`), com um
estado por etapa, como pede a secção 9.4 do modelo Gaia:

    CONSULTAR -> CHAMAR -> NEGOCIAR -> AGUARDAR -> ENCERRAR
        |           |          |
        +-----------+----------+--> ENCERRAR (sem ofertas, sem propostas, sem acordo)

- CONSULTAR: pede ao diretório as ofertas do serviço (ConsultarOfertas).
- CHAMAR: envia o CFP aos fornecedores encontrados e recolhe PROPOSE/REFUSE.
- NEGOCIAR: começa pela proposta mais barata. Aceita, contrapropõe (abre com
  60% do preço base) ou desiste e passa ao fornecedor seguinte. Com acordo,
  rejeita as restantes propostas.
- AGUARDAR: espera que o fornecedor confirme a execução. Só então paga
  (regra 4: pagamento só depois de ConfirmarServico). FAILURE: não paga.
- ENCERRAR: regista o resultado; `on_end` liberta o serviço para nova compra.

Fornecedor: `Vendas` guarda as vendas em curso, por thread, e reage a cada
mensagem (é chamado pelo CyclicBehaviour `FornecedorServicos` do líder):

    CFP -> PROPOSE (preço base) ou REFUSE (sem excedente, regra 7)
    PROPOSE do comprador -> ACCEPT-PROPOSAL (>= 70%, reserva) ou PROPOSE (contraproposta)
    ACCEPT-PROPOSAL do comprador -> reserva e pede a execução ao operador
    INFORM/FAILURE do operador -> ConfirmarServico ao comprador (INFORM ou
                                  FAILURE; na falha liberta a reserva)
    INFORM "pagamento" -> recebe a moeda

As regras de preço e de reserva estão em mercado.py.

Todas as mensagens de uma contratação levam o mesmo thread ("cn-B-001"),
que é o id da negociação. O SPADE entrega uma mensagem a todos os behaviours
cujo template coincide, por isso `Vendas` ignora threads que não conhece
(são compras do próprio líder) e o FSM do comprador só recebe o seu thread.
"""

import time
from dataclasses import dataclass, field

from spade.behaviour import FSMBehaviour, State

import mensagens
import mercado
import metricas
import registo
from config import TEMPO_ESPERA_CN, TEMPO_ESPERA_EXECUCAO

# estados do Contract Net do comprador
CONSULTAR = "CONSULTAR"
CHAMAR = "CHAMAR"
NEGOCIAR = "NEGOCIAR"
AGUARDAR = "AGUARDAR"
ENCERRAR = "ENCERRAR"


@dataclass
class Compra:
    """Uma contratação em curso, do lado do comprador.

    Attributes:
        thread (str): Id da negociação, como "cn-B-001".
        servico (str): Recurso a contratar, como "bombas".
        quantidade (int): Unidades que faltam no bairro.
        fornecedores (list): Líderes com ofertas no diretório.
        propostas (list): Propostas recebidas ({fornecedor, preco, quantidade}),
            da mais barata para a mais cara.
        fornecedor (str | None): Fornecedor com quem houve acordo.
        preco (float | None): Preço acordado, por unidade.
        quantidade_acordada (int): Unidades contratadas.
        resultado (str): Como acabou ("em curso", "pago", "sem ofertas"...).
        rodadas (int): Rodadas de contraproposta usadas no acordo.
    """

    thread: str
    servico: str
    quantidade: int
    fornecedores: list = field(default_factory=list)
    propostas: list = field(default_factory=list)
    fornecedor: str | None = None
    preco: float | None = None
    quantidade_acordada: int = 0
    resultado: str = "em curso"
    rodadas: int = 0

    @property
    def total(self):
        """Valor total do contrato (preço por unidade x unidades)."""
        return round((self.preco or 0.0) * self.quantidade_acordada, 2)


async def esperar(state, aceitar, timeout):
    """Recebe mensagens até chegar uma que interesse ou acabar o tempo.

    Args:
        state (State): O estado do FSM que espera.
        aceitar (callable): Recebe uma `mensagens.Recebida` e devolve True se
            for a mensagem esperada. As outras são descartadas.
        timeout (float): Segundos de espera, no total.

    Returns:
        mensagens.Recebida | None: A mensagem, ou None se o tempo acabou.
    """
    limite = time.monotonic() + timeout
    while (falta := limite - time.monotonic()) > 0:
        msg = mensagens.ler(await state.receive(timeout=falta))
        if msg is None:
            return None
        if aceitar(msg):
            return msg
    return None


class Consultar(State):
    """CONSULTAR: pede ao diretório quem vende o serviço."""

    async def run(self):
        """Envia ConsultarOfertas e guarda a lista de fornecedores.
        Sem ofertas, passa a ENCERRAR."""
        lider, c = self.agent, self.agent.compras[self.servico]
        await self.send(mensagens.criar(
            "diretorio", mensagens.REQUEST, mensagens.CONSULTAR_OFERTAS,
            "consultar_ofertas", thread=c.thread, servico=c.servico))
        resposta = await esperar(
            self, lambda m: m.protocolo == mensagens.CONSULTAR_OFERTAS, TEMPO_ESPERA_CN)
        ofertas = resposta.corpo.get("ofertas", []) if resposta else []
        for oferta in ofertas:
            nome = oferta["fornecedor"]
            if nome not in c.fornecedores and lider.rede.pode_comunicar(lider.nome, nome):
                c.fornecedores.append(nome)
        if not c.fornecedores:
            c.resultado = "sem ofertas no diretório"
            self.set_next_state(ENCERRAR)
            return
        registo.detalhe(lider.nome, f"{c.thread}: {c.servico} à venda em "
                                    f"{', '.join(c.fornecedores)}")
        self.set_next_state(CHAMAR)


class Chamar(State):
    """CHAMAR: envia o CFP e recolhe as propostas."""

    async def run(self):
        """Envia o CFP a todos os fornecedores e espera PROPOSE ou REFUSE de
        cada um (quem não responde a tempo fica de fora)."""
        c = self.agent.compras[self.servico]
        for fornecedor in c.fornecedores:
            await self.send(mensagens.criar(
                fornecedor, mensagens.CFP, mensagens.CONTRACT_NET, "cfp",
                thread=c.thread, servico=c.servico, quantidade=c.quantidade))
        pendentes = set(c.fornecedores)
        while pendentes:
            msg = await esperar(
                self, lambda m: m.protocolo == mensagens.CONTRACT_NET
                and m.remetente in pendentes
                and m.performativa in (mensagens.PROPOSE, mensagens.REFUSE),
                TEMPO_ESPERA_CN)
            if msg is None:
                break
            pendentes.discard(msg.remetente)
            if msg.performativa == mensagens.PROPOSE:
                c.propostas.append({"fornecedor": msg.remetente,
                                    "preco": float(msg.corpo["preco"]),
                                    "quantidade": int(msg.corpo["quantidade"])})
        c.propostas.sort(key=lambda p: (p["preco"], -p["quantidade"], p["fornecedor"]))
        if not c.propostas:
            c.resultado = "nenhum fornecedor fez proposta"
            self.set_next_state(ENCERRAR)
            return
        self.set_next_state(NEGOCIAR)


class Negociar(State):
    """NEGOCIAR: contrapropostas com cada fornecedor, do mais barato ao mais caro."""

    async def run(self):
        """Tenta um acordo com cada proposta, por ordem de preço. Com acordo,
        rejeita as restantes e passa a AGUARDAR; sem acordo, a ENCERRAR."""
        lider, c = self.agent, self.agent.compras[self.servico]
        for indice, proposta in enumerate(c.propostas):
            if await self.negociar_com(proposta):
                for outra in c.propostas[indice + 1:]:
                    await self.send(self.mensagem(outra["fornecedor"],
                                                  mensagens.REJECT_PROPOSAL,
                                                  "rejeicao", motivo="outra proposta"))
                lider.moeda_comprometida += c.total
                registo.evento("CONTRATO", f"bairro {lider.bairro} contratou "
                               f"{c.servico} x{c.quantidade_acordada} ao bairro "
                               f"{c.fornecedor[-1].upper()} a {c.preco:.2f}/un. "
                               f"(base {mercado.preco_base(c.servico):.0f}, "
                               f"{c.rodadas} rodada(s))")
                self.set_next_state(AGUARDAR)
                return
        c.resultado = "sem acordo de preço"
        self.set_next_state(ENCERRAR)

    def mensagem(self, para, performativa, tipo, **dados):
        """Mensagem ao fornecedor nesta contratação (protocolo e thread)."""
        c = self.agent.compras[self.servico]
        return mensagens.criar(para, performativa, mensagens.CONTRACT_NET, tipo,
                               thread=c.thread, servico=c.servico, **dados)

    async def negociar_com(self, proposta):
        """Rodadas de contraproposta com um fornecedor.

        Args:
            proposta (dict): {fornecedor, preco, quantidade} recebida no CHAMAR.

        Returns:
            bool: True se houve acordo (fica guardado na `Compra`).
        """
        lider, c = self.agent, self.agent.compras[self.servico]
        fornecedor, quantidade = proposta["fornecedor"], proposta["quantidade"]
        preco_pedido, ultima_oferta, rodada = proposta["preco"], None, 1
        while True:
            disponivel = lider.estado.moeda - lider.moeda_comprometida
            decisao, preco = mercado.decisao_comprador(
                c.servico, preco_pedido, quantidade, disponivel, rodada, ultima_oferta)
            if decisao == mercado.DESISTIR:
                await self.send(self.mensagem(fornecedor, mensagens.REJECT_PROPOSAL,
                                              "rejeicao", motivo="preço"))
                registo.detalhe(lider.nome, f"{c.thread}: desistiu de {fornecedor} "
                                            f"(pedia {preco_pedido})")
                return False
            if decisao == mercado.ACEITAR:
                await self.send(self.mensagem(fornecedor, mensagens.ACCEPT_PROPOSAL,
                                              "aceitacao", preco=preco,
                                              quantidade=quantidade))
                self.fechar(fornecedor, preco, quantidade, rodada)
                return True

            # contraproposta do comprador
            await self.send(self.mensagem(fornecedor, mensagens.PROPOSE,
                                          "contraproposta", preco=preco,
                                          quantidade=quantidade, rodada=rodada))
            registo.detalhe(lider.nome, f"{c.thread}: rodada {rodada}, {fornecedor} "
                                        f"pede {preco_pedido}, oferece {preco}")
            ultima_oferta = preco
            resposta = await esperar(
                self, lambda m: m.protocolo == mensagens.CONTRACT_NET
                and m.remetente == fornecedor
                and m.performativa in (mensagens.ACCEPT_PROPOSAL, mensagens.PROPOSE,
                                       mensagens.REFUSE, mensagens.FAILURE),
                TEMPO_ESPERA_CN)
            if resposta is None or resposta.performativa in (mensagens.REFUSE,
                                                             mensagens.FAILURE):
                return False
            if resposta.performativa == mensagens.ACCEPT_PROPOSAL:
                # o fornecedor aceitou a contraproposta e já reservou
                self.fechar(fornecedor, preco, int(resposta.corpo.get("quantidade",
                                                                      quantidade)), rodada)
                return True
            preco_pedido = float(resposta.corpo["preco"])       # nova contraproposta
            rodada += 1

    def fechar(self, fornecedor, preco, quantidade, rodada):
        """Guarda o acordo na `Compra`."""
        c = self.agent.compras[self.servico]
        c.fornecedor, c.preco, c.quantidade_acordada, c.rodadas = (
            fornecedor, preco, quantidade, rodada)


class Aguardar(State):
    """AGUARDAR: espera a confirmação da execução e só então paga."""

    async def run(self):
        """INFORM "servico_confirmado": paga (moeda do comprador desce) e
        envia o Pagamento. FAILURE ou silêncio: não paga (regra 4)."""
        lider, c = self.agent, self.agent.compras[self.servico]
        msg = await esperar(
            self, lambda m: m.protocolo == mensagens.CONTRACT_NET
            and m.remetente == c.fornecedor
            and m.performativa in (mensagens.INFORM, mensagens.FAILURE),
            TEMPO_ESPERA_EXECUCAO)
        lider.moeda_comprometida = max(0.0, lider.moeda_comprometida - c.total)
        if msg is None or msg.performativa == mensagens.FAILURE:
            motivo = msg.corpo.get("motivo", "falha") if msg else "sem confirmação"
            c.resultado = f"serviço falhou ({motivo}), sem pagamento"
            registo.evento("CONTRATO", f"bairro {lider.bairro}: {c.servico} de "
                                       f"{c.fornecedor} falhou ({motivo}); não paga")
            self.set_next_state(ENCERRAR)
            return

        lider.estado.moeda = round(lider.estado.moeda - c.total, 2)
        await self.send(mensagens.criar(
            c.fornecedor, mensagens.INFORM, mensagens.CONTRACT_NET, "pagamento",
            thread=c.thread, servico=c.servico, valor=c.total))
        metricas.transacao(lider.bairro, c.fornecedor[-1].upper(), c.servico,
                           c.quantidade_acordada, c.preco)
        c.resultado = "pago"
        registo.evento("PAGAMENTO", f"bairro {lider.bairro} pagou {c.total:.2f} ao "
                                    f"bairro {c.fornecedor[-1].upper()} "
                                    f"(saldo {lider.estado.moeda:.2f})")
        self.set_next_state(ENCERRAR)


class Encerrar(State):
    """ENCERRAR: regista como acabou a contratação."""

    async def run(self):
        """Escreve o resultado no registo detalhado."""
        c = self.agent.compras[self.servico]
        if c.resultado != "pago":
            registo.detalhe(self.agent.nome, f"{c.thread} ({c.servico}): {c.resultado}")


class ContractNetComprador(FSMBehaviour):
    """Uma contratação de um serviço, do lado do comprador.

    Attributes:
        servico (str): O serviço contratado (chave em `lider.compras`).
    """

    def __init__(self, servico):
        """Cria o FSM com os estados do Contract Net.

        Args:
            servico (str): O serviço a contratar.
        """
        super().__init__()
        self.servico = servico
        for nome, estado, inicial in ((CONSULTAR, Consultar(), True),
                                      (CHAMAR, Chamar(), False),
                                      (NEGOCIAR, Negociar(), False),
                                      (AGUARDAR, Aguardar(), False),
                                      (ENCERRAR, Encerrar(), False)):
            estado.servico = servico
            self.add_state(nome, estado, initial=inicial)
        for origem, destino in ((CONSULTAR, CHAMAR), (CONSULTAR, ENCERRAR),
                                (CHAMAR, NEGOCIAR), (CHAMAR, ENCERRAR),
                                (NEGOCIAR, AGUARDAR), (NEGOCIAR, ENCERRAR),
                                (AGUARDAR, ENCERRAR)):
            self.add_transition(origem, destino)

    async def on_end(self):
        """Liberta o serviço para uma nova compra e guarda o histórico."""
        compra = self.agent.compras.pop(self.servico, None)
        if compra is not None:
            self.agent.historico_compras.append(compra)


def template_comprador(thread):
    """Template do FSM do comprador: só mensagens da sua contratação.

    Args:
        thread (str): Id da negociação.

    Returns:
        spade.template.Template: Respostas do diretório e dos fornecedores.
    """
    return (mensagens.template(mensagens.CONSULTAR_OFERTAS, mensagens.INFORM,
                               mensagens.REFUSE, thread=thread)
            | mensagens.template(mensagens.CONTRACT_NET, mensagens.PROPOSE,
                                 mensagens.REFUSE, mensagens.ACCEPT_PROPOSAL,
                                 mensagens.INFORM, mensagens.FAILURE, thread=thread))


# ---- Fornecedor -------------------------------------------------------------

@dataclass
class Venda:
    """Uma venda em curso, do lado do fornecedor.

    Attributes:
        thread (str): Id da negociação (criado pelo comprador).
        comprador (str): Nome do líder comprador, em minúsculas.
        servico (str): Recurso vendido.
        quantidade (int): Unidades propostas.
        preco (float): Último preço pedido, ou o acordado.
        fase (str): "negociando", "executando" ou "confirmada".
    """

    thread: str
    comprador: str
    servico: str
    quantidade: int
    preco: float
    fase: str = "negociando"


class Vendas:
    """O papel Fornecedor do líder: responde ao Contract Net dos outros bairros.

    Cada método recebe uma mensagem já lida e devolve a lista de mensagens a
    enviar, para o behaviour as enviar e para se poder testar sem rede.

    Attributes:
        lider (CommunityLeader): O líder dono destas vendas.
        abertas (dict): Vendas em curso, por thread.
    """

    def __init__(self, lider):
        """Cria o registo de vendas vazio.

        Args:
            lider (CommunityLeader): O líder fornecedor.
        """
        self.lider = lider
        self.abertas = {}

    def tratar(self, msg):
        """Encaminha uma mensagem do Contract Net ou do operador.

        Args:
            msg (mensagens.Recebida): Mensagem recebida pelo líder.

        Returns:
            list: Mensagens a enviar (pode ser vazia).
        """
        if msg.protocolo == mensagens.EXECUTAR_SERVICO:
            return self.resultado_execucao(msg)
        if msg.performativa == mensagens.CFP:
            return self.cfp(msg)
        venda = self.abertas.get(msg.thread)
        if venda is None or msg.remetente != venda.comprador:
            return []               # compra do próprio líder, ou lixo
        if msg.performativa == mensagens.PROPOSE and venda.fase == "negociando":
            return self.contraproposta(venda, msg)
        if msg.performativa == mensagens.ACCEPT_PROPOSAL and venda.fase == "negociando":
            return self.aceite_pelo_comprador(venda, msg)
        if msg.performativa == mensagens.REJECT_PROPOSAL and venda.fase == "negociando":
            del self.abertas[venda.thread]
            return []
        if msg.performativa == mensagens.INFORM and msg.tipo == "pagamento":
            return self.pagamento(venda, msg)
        return []

    def _para_comprador(self, venda, performativa, tipo, **dados):
        """Mensagem ao comprador, no thread da venda."""
        return mensagens.criar(venda.comprador, performativa, mensagens.CONTRACT_NET,
                               tipo, thread=venda.thread, servico=venda.servico, **dados)

    def cfp(self, msg):
        """CFP: propõe o preço base se houver excedente (regra 7), senão REFUSE."""
        lider = self.lider
        servico, pedida = msg.corpo.get("servico"), int(msg.corpo.get("quantidade", 0))
        if not lider.rede.pode_comunicar(lider.nome, msg.remetente):
            return []
        disponivel = mercado.excedente(lider.estado, servico, lider.risco_do_bairro)
        quantidade = min(pedida, disponivel)
        if quantidade <= 0:
            return [mensagens.criar(msg.remetente, mensagens.REFUSE,
                                    mensagens.CONTRACT_NET, "recusa", thread=msg.thread,
                                    servico=servico, motivo="sem excedente")]
        venda = Venda(msg.thread, msg.remetente, servico, quantidade,
                      mercado.preco_pedido_inicial(servico))
        self.abertas[msg.thread] = venda
        return [self._para_comprador(venda, mensagens.PROPOSE, "proposta",
                                     preco=venda.preco, quantidade=quantidade)]

    def contraproposta(self, venda, msg):
        """Contraproposta do comprador: aceita a partir de 70% (regra 9),
        senão contrapõe."""
        oferta = float(msg.corpo["preco"])
        if mercado.vendedor_aceita(venda.servico, oferta):
            venda.preco = oferta
            return self.reservar_e_executar(venda, avisar_aceite=True)
        venda.preco = mercado.contraproposta_vendedor(venda.servico, venda.preco, oferta)
        return [self._para_comprador(venda, mensagens.PROPOSE, "proposta",
                                     preco=venda.preco, quantidade=venda.quantidade)]

    def aceite_pelo_comprador(self, venda, msg):
        """O comprador aceitou o preço pedido: reserva e pede a execução."""
        if not mercado.vendedor_aceita(venda.servico, float(msg.corpo.get("preco", 0))):
            del self.abertas[venda.thread]
            return [self._para_comprador(venda, mensagens.FAILURE, "falha",
                                         motivo="preço diferente do proposto")]
        return self.reservar_e_executar(venda, avisar_aceite=False)

    def reservar_e_executar(self, venda, avisar_aceite):
        """Passos 4 e 5 do Contract Net: reserva o recurso e pede ao operador
        do bairro que execute o serviço no bairro comprador.

        A reserva volta a verificar a regra 7 com o estoque atual (outra venda
        pode ter reservado entretanto).

        Args:
            venda (Venda): A venda acordada.
            avisar_aceite (bool): Se True, envia ACCEPT-PROPOSAL ao comprador
                (foi o fornecedor que aceitou a contraproposta).

        Returns:
            list: Mensagens a enviar.
        """
        lider = self.lider
        operador = f"op{lider.bairro}"
        if (not mercado.pode_oferecer(lider.estado, venda.servico, venda.quantidade,
                                      lider.risco_do_bairro)
                or not lider.rede.pode_comunicar(lider.nome, operador)
                or not lider.estado.reservar(venda.servico, venda.quantidade)):
            del self.abertas[venda.thread]
            return [self._para_comprador(venda, mensagens.FAILURE, "falha",
                                         motivo="sem estoque para reservar")]
        venda.fase = "executando"
        registo.detalhe(lider.nome, f"{venda.thread}: reservou {venda.servico} "
                                    f"x{venda.quantidade} a {venda.preco}")
        enviar = []
        if avisar_aceite:
            enviar.append(self._para_comprador(venda, mensagens.ACCEPT_PROPOSAL,
                                               "aceitacao", preco=venda.preco,
                                               quantidade=venda.quantidade))
        comprador = venda.comprador[-1].upper()
        enviar.append(mensagens.criar(
            operador, mensagens.REQUEST, mensagens.EXECUTAR_SERVICO, "executar_servico",
            thread=venda.thread, servico=venda.servico, quantidade=venda.quantidade,
            destino=comprador))
        return enviar

    def resultado_execucao(self, msg):
        """Resposta do operador: confirma ao comprador (ConfirmarServico) ou,
        na falha, liberta a reserva e avisa o comprador."""
        venda = self.abertas.get(msg.thread)
        if venda is None or venda.fase != "executando":
            return []
        if msg.performativa == mensagens.AGREE:
            return []
        if msg.performativa == mensagens.INFORM:
            venda.fase = "confirmada"
            return [self._para_comprador(venda, mensagens.INFORM, "servico_confirmado",
                                         quantidade=venda.quantidade, preco=venda.preco)]
        # FAILURE: a reserva volta ao estoque livre e não há pagamento
        self.lider.estado.libertar(venda.servico, venda.quantidade)
        del self.abertas[venda.thread]
        motivo = msg.corpo.get("motivo", "falha na execução")
        return [self._para_comprador(venda, mensagens.FAILURE, "falha", motivo=motivo)]

    def pagamento(self, venda, msg):
        """Pagamento do comprador: a moeda do fornecedor sobe."""
        if venda.fase != "confirmada":
            return []
        valor = float(msg.corpo.get("valor", 0.0))
        self.lider.estado.moeda = round(self.lider.estado.moeda + valor, 2)
        del self.abertas[venda.thread]
        registo.detalhe(self.lider.nome, f"{venda.thread}: recebeu {valor:.2f} "
                                         f"(saldo {self.lider.estado.moeda:.2f})")
        return []
