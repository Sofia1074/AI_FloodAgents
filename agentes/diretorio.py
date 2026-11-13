"""Agente 4 — Diretório de Serviços (existe um só).

Papel Gaia: Diretorio (docs/gaia_detalhado.md, secções 9.1.3 e 9.2.2).

    Diretorio = (GerirOferta | ConsultarOfertas)ω

O diretório é um serviço **passivo**: guarda as ofertas dos bairros (serviço,
preço, fornecedor, quantidade disponível) e responde às consultas dos líderes.
Não negoceia, não escolhe fornecedores e não mexe em estoque nem em moeda:
isso é do Contract Net, entre os líderes (secção 5.3 do guia).

Protocolos que atende (um só behaviour, `AtenderPedidos`, filtrado por Template):

- GerirOferta (Fornecedor -> Diretorio): REQUEST com o tipo
  "publicar_oferta", "atualizar_oferta" ou "remover_oferta".
  Resposta AGREE ("oferta_registada" / "oferta_removida") ou
  REFUSE ("oferta_recusada", com o motivo).
- ConsultarOfertas (Comprador -> Diretorio): REQUEST "consultar_ofertas"
  com o serviço procurado (e, opcionalmente, a quantidade mínima).
  Resposta INFORM "lista_ofertas", da mais barata para a mais cara, com o
  preço base de referência (o comprador abre com cerca de 60% dele).

Regras organizacionais garantidas aqui (secção 9.1.5):

- Regra 11 (segurança): uma oferta só muda a pedido do Fornecedor que a
  publicou. O dono é sempre o **remetente** da mensagem (JID), nunca um campo
  do corpo, por isso um líder não consegue alterar a oferta de outro.
- Regra 10: comprador e fornecedor pertencem a bairros diferentes. A consulta
  nunca devolve ao líder as ofertas do seu próprio bairro.
- Só os líderes comunitários (papel Fornecedor) publicam ofertas.

A reserva mínima (secção 3 do guia) é responsabilidade do líder fornecedor:
ele só publica, ou só mantém, a quantidade que pode dispensar. O diretório
apenas guarda o que lhe dizem; uma oferta com quantidade 0 fica registada
mas indisponível e não aparece nas consultas.

A lógica do registo (`RegistoOfertas`) não depende do SPADE, para se poder
testar sem servidor XMPP.

Exemplo (no líder fornecedor):
    await self.send(mensagens.criar(
        "diretorio", mensagens.REQUEST, mensagens.GERIR_OFERTA,
        "publicar_oferta", thread=mensagens.novo_id("of-A"),
        servico="bombas", preco=20.0, quantidade=2))

Exemplo (no líder comprador):
    await self.send(mensagens.criar(
        "diretorio", mensagens.REQUEST, mensagens.CONSULTAR_OFERTAS,
        "consultar_ofertas", thread=mensagens.novo_id("cons-B"),
        servico="bombas", quantidade=1))
"""

import itertools
import time
from dataclasses import asdict, dataclass, field

import mensagens
import registo
from config import EFEITO_RECURSO, PASSWORD, jid

# Preços base fictícios (secção 5.3 do guia). As barreiras não têm preço no
# guia: podem ser oferecidas, mas sem preço de referência (None).
PRECO_BASE = {
    "sacos_areia": 10.0,   # por lote
    "bombas": 20.0,
    "equipas": 30.0,
    "barreiras": None,
}
# serviços que o diretório aceita: os recursos que existem no ambiente
SERVICOS = set(EFEITO_RECURSO)


@dataclass
class Oferta:
    """Uma oferta publicada no diretório.

    Attributes:
        id_oferta (str): Id da oferta, como "of-001".
        fornecedor (str): Nome do líder que a publicou (em minúsculas), como "lidera".
        bairro (str): Bairro do fornecedor, "A", "B" ou "C".
        servico (str): Um dos SERVICOS, como "bombas".
        preco (float): Preço pedido por unidade (ou por lote, nos sacos de areia).
        quantidade (int): Unidades que o bairro pode dispensar agora.
        atualizada (float): Instante (time.monotonic) da última alteração.
    """

    id_oferta: str
    fornecedor: str
    bairro: str
    servico: str
    preco: float
    quantidade: int
    atualizada: float = field(default_factory=time.monotonic)

    @property
    def disponivel(self):
        """True se ainda há unidades para contratar."""
        return self.quantidade > 0

    def para_mensagem(self):
        """Converte a oferta no dicionário que segue no corpo JSON.

        Returns:
            dict: Campos da oferta, incluindo `disponivel` e o `preco_base`.
        """
        dados = asdict(self)
        dados.pop("atualizada")
        dados["disponivel"] = self.disponivel
        dados["preco_base"] = PRECO_BASE.get(self.servico)
        return dados


def bairro_de(nome):
    """Bairro de um líder, a partir do nome do agente.

    Args:
        nome (str): Nome do agente, como "liderA" ou "lidera".

    Returns:
        str | None: "A", "B" ou "C", ou None se não for um líder.
    """
    nome = (nome or "").lower()
    if not nome.startswith("lider") or len(nome) != len("lider") + 1:
        return None
    bairro = nome[-1].upper()
    return bairro if bairro in "ABC" else None


def validar_campos(servico=None, preco=None, quantidade=None):
    """Verifica os campos de uma oferta (só os que vierem preenchidos).

    Args:
        servico (str | None): Nome do serviço.
        preco (float | None): Preço por unidade.
        quantidade (int | None): Unidades disponíveis.

    Returns:
        str | None: O motivo da recusa, ou None se estiver tudo bem.
    """
    if servico is not None and servico not in SERVICOS:
        return f"serviço desconhecido: {servico}"
    if preco is not None:
        if isinstance(preco, bool) or not isinstance(preco, (int, float)) or preco <= 0:
            return "o preço tem de ser um número positivo"
    if quantidade is not None:
        if isinstance(quantidade, bool) or not isinstance(quantidade, int) or quantidade < 0:
            return "a quantidade tem de ser um inteiro maior ou igual a 0"
    return None


class RegistoOfertas:
    """O registo de ofertas (recurso `registro_ofertas` do modelo Gaia).

    Cada fornecedor tem no máximo uma oferta por serviço: publicar de novo o
    mesmo serviço substitui a oferta anterior (mantém o id).

    Todos os métodos que alteram o registo recebem o `fornecedor` que fez o
    pedido e recusam se ele não for o dono da oferta (regra 11).

    Attributes:
        ofertas (dict): Ofertas publicadas, por id (`id_oferta` -> `Oferta`).
    """

    def __init__(self):
        """Cria o registo vazio."""
        self.ofertas = {}                     # id_oferta -> Oferta
        self._ids = itertools.count(1)

    def _da_oferta(self, fornecedor, servico):
        """Procura a oferta que o fornecedor já tem para um serviço.

        Args:
            fornecedor (str): Nome do líder, em minúsculas.
            servico (str): Serviço da oferta.

        Returns:
            Oferta | None: A oferta, ou None se o fornecedor não tiver nenhuma.
        """
        for oferta in self.ofertas.values():
            if oferta.fornecedor == fornecedor and oferta.servico == servico:
                return oferta
        return None

    def _do_dono(self, fornecedor, id_oferta=None, servico=None):
        """Encontra a oferta a alterar e confirma que o pedido vem do dono.

        A oferta identifica-se pelo id ou, na falta dele, pelo serviço.

        Args:
            fornecedor (str): Nome do líder que pede, em minúsculas.
            id_oferta (str | None): Id da oferta.
            servico (str | None): Alternativa ao id: o serviço da oferta.

        Returns:
            tuple: (Oferta | None, motivo da recusa | None).
        """
        if id_oferta is not None:
            oferta = self.ofertas.get(id_oferta)
        elif servico is not None:
            oferta = self._da_oferta(fornecedor, servico)
        else:
            return None, "falta indicar o id da oferta ou o serviço"
        if oferta is None:
            return None, "oferta inexistente"
        if oferta.fornecedor != fornecedor:
            # regra 11: só o fornecedor que publicou altera a oferta
            return None, "só o fornecedor que publicou a oferta a pode alterar"
        return oferta, None

    def publicar(self, fornecedor, servico, preco, quantidade):
        """Publica uma oferta, ou substitui a que o fornecedor já tinha.

        Args:
            fornecedor (str): Nome do líder que pede, como "lidera".
            servico (str): Um dos SERVICOS.
            preco (float): Preço por unidade.
            quantidade (int): Unidades que o bairro pode dispensar.

        Returns:
            tuple: (Oferta | None, motivo da recusa | None).
        """
        fornecedor = fornecedor.lower()
        bairro = bairro_de(fornecedor)
        if bairro is None:
            return None, "só os líderes comunitários publicam ofertas"
        if servico is None or preco is None or quantidade is None:
            return None, "a oferta precisa de serviço, preço e quantidade"
        motivo = validar_campos(servico, preco, quantidade)
        if motivo:
            return None, motivo

        oferta = self._da_oferta(fornecedor, servico)
        if oferta is None:
            oferta = Oferta(f"of-{next(self._ids):03d}", fornecedor, bairro,
                            servico, float(preco), quantidade)
            self.ofertas[oferta.id_oferta] = oferta
        else:
            oferta.preco = float(preco)
            oferta.quantidade = quantidade
            oferta.atualizada = time.monotonic()
        return oferta, None

    def atualizar(self, fornecedor, id_oferta=None, servico=None,
                  preco=None, quantidade=None):
        """Muda o preço e/ou a quantidade de uma oferta existente.

        Usado pelo fornecedor quando reserva ou gasta estoque num contrato,
        ou quando muda o preço.

        Args:
            fornecedor (str): Nome do líder que pede.
            id_oferta (str | None): Id da oferta a mudar.
            servico (str | None): Alternativa ao id: o serviço da oferta.
            preco (float | None): Novo preço, se mudar.
            quantidade (int | None): Nova quantidade, se mudar.

        Returns:
            tuple: (Oferta | None, motivo da recusa | None).
        """
        fornecedor = fornecedor.lower()
        oferta, motivo = self._do_dono(fornecedor, id_oferta, servico)
        if motivo:
            return None, motivo
        if preco is None and quantidade is None:
            return None, "nada para atualizar (preço ou quantidade)"
        motivo = validar_campos(preco=preco, quantidade=quantidade)
        if motivo:
            return None, motivo
        if preco is not None:
            oferta.preco = float(preco)
        if quantidade is not None:
            oferta.quantidade = quantidade
        oferta.atualizada = time.monotonic()
        return oferta, None

    def remover(self, fornecedor, id_oferta=None, servico=None):
        """Retira uma oferta do diretório.

        Args:
            fornecedor (str): Nome do líder que pede.
            id_oferta (str | None): Id da oferta a remover.
            servico (str | None): Alternativa ao id: o serviço da oferta.

        Returns:
            tuple: (Oferta removida | None, motivo da recusa | None).
        """
        fornecedor = fornecedor.lower()
        oferta, motivo = self._do_dono(fornecedor, id_oferta, servico)
        if motivo:
            return None, motivo
        del self.ofertas[oferta.id_oferta]
        return oferta, None

    def consultar(self, servico=None, quantidade=0, pedido_por=None):
        """Lista as ofertas disponíveis, da mais barata para a mais cara.

        Args:
            servico (str | None): Serviço procurado. Sem ele, lista todos.
            quantidade (int): Só ofertas com pelo menos esta quantidade.
                Com 0, basta haver alguma unidade.
            pedido_por (str | None): Líder que consulta. As ofertas do seu
                bairro ficam de fora (regra 10).

        Returns:
            list[Oferta]: As ofertas que servem, ordenadas por preço.
        """
        bairro_comprador = bairro_de(pedido_por)
        encontradas = [
            o for o in self.ofertas.values()
            if o.disponivel
            and (servico is None or o.servico == servico)
            and o.quantidade >= quantidade
            and o.bairro != bairro_comprador
        ]
        return sorted(encontradas, key=lambda o: (o.preco, -o.quantidade, o.id_oferta))


try:
    from spade.agent import Agent
    from spade.behaviour import CyclicBehaviour
except ImportError:          # sem SPADE: o registo continua a funcionar
    Agent = object
    CyclicBehaviour = object


class ServiceDirectory(Agent):
    """Agente 4 — Diretório de Serviços.

    Attributes:
        nome (str): Nome do agente ("diretorio").
        registo_ofertas (RegistoOfertas): As ofertas publicadas.
        pedidos_atendidos (int): Pedidos respondidos (para as métricas).
    """

    def __init__(self, nome="diretorio", password=PASSWORD):
        """Cria o diretório (ainda não o arranca).

        Args:
            nome (str): Nome do agente, que dá o JID.
            password (str): Palavra-passe no servidor XMPP.
        """
        super().__init__(jid(nome), password)
        self.nome = nome
        self.registo_ofertas = RegistoOfertas()
        self.pedidos_atendidos = 0

    class AtenderPedidos(CyclicBehaviour):
        """Recebe os pedidos dos líderes (GerirOferta e ConsultarOfertas) e
        responde a cada um, sem tomar decisões próprias."""

        async def run(self):
            """Espera um pedido e responde no mesmo protocolo e thread."""
            diretorio = self.agent
            msg = mensagens.ler(await self.receive(timeout=1))
            if msg is None:
                return
            resposta = diretorio.atender(msg)
            if resposta is not None:
                await self.send(resposta)
                diretorio.pedidos_atendidos += 1

    async def setup(self):
        """Arranca o behaviour que atende os pedidos.

        O template só deixa passar REQUEST dos protocolos do diretório."""
        registo.detalhe(self.nome, "agente ativo (diretório de serviços)")
        pedidos = (mensagens.template(mensagens.GERIR_OFERTA, mensagens.REQUEST)
                   | mensagens.template(mensagens.CONSULTAR_OFERTAS, mensagens.REQUEST))
        self.add_behaviour(self.AtenderPedidos(), pedidos)

    def atender(self, msg):
        """Trata um pedido já lido e prepara a resposta.

        Args:
            msg (mensagens.Recebida): O pedido de um líder.

        Returns:
            spade.message.Message | None: A resposta a enviar, ou None se o
            pedido não for para o diretório.
        """
        if msg.protocolo == mensagens.GERIR_OFERTA:
            return self.gerir_oferta(msg)
        if msg.protocolo == mensagens.CONSULTAR_OFERTAS:
            return self.consultar_ofertas(msg)
        return None

    def _responder(self, msg, performativa, tipo, **dados):
        """Cria a resposta ao remetente, no mesmo protocolo e thread do pedido.

        Args:
            msg (mensagens.Recebida): O pedido a que se responde.
            performativa (str): Performativa da resposta, como "agree".
            tipo (str): Tipo do conteúdo, como "oferta_registada".
            **dados: Restantes campos do corpo.

        Returns:
            spade.message.Message: A resposta pronta a enviar.
        """
        return mensagens.criar(msg.remetente, performativa, msg.protocolo, tipo,
                               thread=msg.thread, **dados)

    def gerir_oferta(self, msg):
        """Protocolo GerirOferta: publicar, atualizar ou remover uma oferta.

        O dono da oferta é sempre o remetente da mensagem (regra 11).

        Args:
            msg (mensagens.Recebida): REQUEST "publicar_oferta",
                "atualizar_oferta" ou "remover_oferta".

        Returns:
            spade.message.Message: AGREE com a oferta, ou REFUSE com o motivo.
        """
        c = msg.corpo
        fornecedor = msg.remetente
        if msg.tipo == "publicar_oferta":
            oferta, motivo = self.registo_ofertas.publicar(
                fornecedor, c.get("servico"), c.get("preco"), c.get("quantidade"))
        elif msg.tipo == "atualizar_oferta":
            oferta, motivo = self.registo_ofertas.atualizar(
                fornecedor, c.get("id_oferta"), c.get("servico"),
                c.get("preco"), c.get("quantidade"))
        elif msg.tipo == "remover_oferta":
            oferta, motivo = self.registo_ofertas.remover(
                fornecedor, c.get("id_oferta"), c.get("servico"))
        else:
            oferta, motivo = None, f"pedido desconhecido: {msg.tipo}"

        if motivo:
            registo.detalhe(self.nome, f"recusou {msg.tipo} de {fornecedor}: {motivo}")
            return self._responder(msg, mensagens.REFUSE, "oferta_recusada",
                                   pedido=msg.tipo, motivo=motivo,
                                   id_oferta=c.get("id_oferta"))

        if msg.tipo == "remover_oferta":
            registo.evento("OFERTA", f"bairro {oferta.bairro} retirou a oferta de "
                                     f"{oferta.servico} ({oferta.id_oferta})")
            return self._responder(msg, mensagens.AGREE, "oferta_removida",
                                   id_oferta=oferta.id_oferta)

        texto = (f"{oferta.servico} x{oferta.quantidade} a {oferta.preco:.1f} "
                 f"({oferta.id_oferta})")
        if msg.tipo == "publicar_oferta":
            registo.evento("OFERTA", f"bairro {oferta.bairro} oferece {texto}")
        else:
            registo.detalhe(self.nome, f"bairro {oferta.bairro} atualizou {texto}")
        return self._responder(msg, mensagens.AGREE, "oferta_registada",
                               **oferta.para_mensagem())

    def consultar_ofertas(self, msg):
        """Protocolo ConsultarOfertas: devolve a lista de fornecedores e preços.

        Args:
            msg (mensagens.Recebida): REQUEST "consultar_ofertas", com
                `servico` (opcional) e `quantidade` (opcional, por omissão 0).

        Returns:
            spade.message.Message: INFORM "lista_ofertas" (pode vir vazia), ou
            REFUSE se o pedido estiver mal formado.
        """
        servico = msg.corpo.get("servico")
        quantidade = msg.corpo.get("quantidade", 0) or 0
        motivo = validar_campos(servico=servico, quantidade=quantidade)
        if msg.tipo != "consultar_ofertas":
            motivo = f"pedido desconhecido: {msg.tipo}"
        if motivo:
            registo.detalhe(self.nome, f"recusou consulta de {msg.remetente}: {motivo}")
            return self._responder(msg, mensagens.REFUSE, "consulta_recusada",
                                   motivo=motivo)

        ofertas = self.registo_ofertas.consultar(servico, quantidade, msg.remetente)
        registo.detalhe(self.nome, f"{msg.remetente} consultou {servico or 'tudo'}: "
                                   f"{len(ofertas)} oferta(s)")
        return self._responder(
            msg, mensagens.INFORM, "lista_ofertas",
            servico=servico, quantidade=quantidade,
            preco_base=PRECO_BASE.get(servico) if servico else None,
            ofertas=[o.para_mensagem() for o in ofertas])
