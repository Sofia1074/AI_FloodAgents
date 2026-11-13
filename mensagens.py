"""Criar e ler as mensagens trocadas entre os agentes.

Todas as mensagens do sistema seguem o mesmo formato (secção 9.2.3 do guia
Gaia e "Convenções" do plano de tarefas):

    metadados SPADE   performative  o que a mensagem significa (FIPA-ACL)
                      protocol      a conversa a que pertence (negociar-descarga...)
                      thread        id da conversa (desc-007, cn-A-003...)
    corpo             JSON, sempre com o campo "tipo"

Os agentes não montam mensagens à mão: usam `criar()` para enviar,
`ler()` para receber e `template()` para que cada behaviour só receba o
seu protocolo.

O SPADE só é importado dentro de `criar()` e `template()`. Assim o resto do
módulo, e os testes, funcionam sem o SPADE instalado.

Exemplo (num behaviour):
    msg = mensagens.criar("liderA", "propose", "negociar-descarga",
                          "proposta_descarga", thread="desc-007",
                          id_proposta="desc-007-r1", rodada=1, caudal=40.0)
    await self.send(msg)
    ...
    recebida = mensagens.ler(await self.receive(timeout=1))
    if recebida and recebida.tipo == "voto":
        ...
"""

import itertools
import json
from dataclasses import dataclass, field

import registo
from config import jid

# Performativas FIPA-ACL usadas no sistema (secção 4 do guia)
INFORM = "inform"
REQUEST = "request"
AGREE = "agree"
REFUSE = "refuse"
CFP = "cfp"
PROPOSE = "propose"
ACCEPT_PROPOSAL = "accept-proposal"
REJECT_PROPOSAL = "reject-proposal"
FAILURE = "failure"
PERFORMATIVAS = {INFORM, REQUEST, AGREE, REFUSE, CFP, PROPOSE,
                 ACCEPT_PROPOSAL, REJECT_PROPOSAL, FAILURE}

# Protocolos (um behaviour por protocolo, filtrado por Template)
ALERTA_RISCO = "alerta-risco"
PEDIR_MITIGACAO = "pedir-mitigacao"
NEGOCIAR_DESCARGA = "negociar-descarga"
VOTACAO = "votacao"
GERIR_OFERTA = "gerir-oferta"
CONSULTAR_OFERTAS = "consultar-ofertas"
CONTRACT_NET = "contract-net"
EXECUTAR_SERVICO = "executar-servico"
PROTOCOLOS = {ALERTA_RISCO, PEDIR_MITIGACAO, NEGOCIAR_DESCARGA, VOTACAO,
              GERIR_OFERTA, CONSULTAR_OFERTAS, CONTRACT_NET, EXECUTAR_SERVICO}

_contadores = {}


def novo_id(prefixo):
    """Gera o id de uma conversa nova, para usar como `thread`.

    Args:
        prefixo (str): Parte fixa do id, por exemplo "desc" ou "cn-A".

    Returns:
        str: Id único dentro desta execução, como "desc-001", "desc-002"...
    """
    contador = _contadores.setdefault(prefixo, itertools.count(1))
    return f"{prefixo}-{next(contador):03d}"


def montar_corpo(tipo, dados=None):
    """Converte o tipo e os dados da mensagem no texto JSON do corpo.

    Args:
        tipo (str): Nome do tipo de mensagem, por exemplo "proposta_descarga".
        dados (dict | None): Restantes campos da mensagem.

    Returns:
        str: JSON com o campo "tipo" e os dados.
    """
    return json.dumps({"tipo": tipo, **(dados or {})})


def interpretar_corpo(texto):
    """Converte o texto JSON do corpo num dicionário, sem nunca rebentar.

    Args:
        texto (str | None): Corpo de uma mensagem recebida.

    Returns:
        dict | None: O dicionário, ou None se o texto estiver vazio, não for
        JSON, não for um objeto JSON ou não tiver o campo "tipo".
    """
    try:
        corpo = json.loads(texto)
    except (TypeError, ValueError):
        return None
    if not isinstance(corpo, dict) or "tipo" not in corpo:
        return None
    return corpo


def criar(para, performativa, protocolo, tipo, thread=None, **dados):
    """Cria a mensagem SPADE pronta a enviar com `await self.send(msg)`.

    Args:
        para (str): Nome do destinatário, como "liderA" (o JID é calculado).
        performativa (str): Uma das PERFORMATIVAS, por exemplo "propose".
        protocolo (str): Um dos PROTOCOLOS, por exemplo "negociar-descarga".
        tipo (str): Tipo do conteúdo, por exemplo "proposta_descarga".
        thread (str | None): Id da conversa (ver `novo_id`).
        **dados: Campos do corpo, como caudal=40.0 ou rodada=2.

    Returns:
        spade.message.Message: A mensagem com metadados e corpo JSON.

    Raises:
        ValueError: Se a performativa ou o protocolo não existirem. É um erro
            de programação, por isso falha logo em vez de enviar lixo.
    """
    if performativa not in PERFORMATIVAS:
        raise ValueError(f"performativa desconhecida: {performativa!r}")
    if protocolo not in PROTOCOLOS:
        raise ValueError(f"protocolo desconhecido: {protocolo!r}")

    from spade.message import Message
    msg = Message(to=jid(para))
    msg.set_metadata("performative", performativa)
    msg.set_metadata("protocol", protocolo)
    if thread is not None:
        msg.thread = thread
    msg.body = montar_corpo(tipo, dados)
    return msg


@dataclass
class Recebida:
    """Mensagem recebida, já separada nos seus campos.

    Attributes:
        remetente (str): Nome de quem enviou, como "barragem" ou "liderA".
        performativa (str | None): Performativa FIPA da mensagem.
        protocolo (str | None): Protocolo da conversa.
        thread (str | None): Id da conversa.
        tipo (str): Tipo do conteúdo.
        corpo (dict): Todos os campos do corpo, incluindo "tipo".
    """

    remetente: str
    performativa: str | None
    protocolo: str | None
    thread: str | None
    tipo: str
    corpo: dict = field(default_factory=dict)


def ler(msg):
    """Interpreta uma mensagem recebida.

    Nunca lança erro: uma mensagem mal formada devolve None e fica só no
    registo detalhado (-v), em vez de deitar abaixo o behaviour.

    Args:
        msg (spade.message.Message | None): O que `self.receive()` devolveu.

    Returns:
        Recebida | None: A mensagem separada nos campos, ou None se `msg` for
        None (timeout) ou o corpo for inválido.
    """
    if msg is None:
        return None
    corpo = interpretar_corpo(msg.body)
    remetente = msg.sender.user if msg.sender else "?"
    if corpo is None:
        registo.detalhe("mensagens", f"ignorada mensagem inválida de {remetente}")
        return None
    return Recebida(
        remetente=remetente,
        performativa=msg.get_metadata("performative"),
        protocolo=msg.get_metadata("protocol"),
        thread=msg.thread,
        tipo=corpo["tipo"],
        corpo=corpo,
    )


def template(protocolo, *performativas, thread=None):
    """Cria o Template que filtra as mensagens de um behaviour.

    Usa-se em `self.add_behaviour(behaviour, mensagens.template(...))`.
    O behaviour só recebe mensagens deste protocolo (e, se indicadas, com uma
    destas performativas), por isso um voto nunca se confunde com outra coisa.

    Args:
        protocolo (str): Um dos PROTOCOLOS.
        *performativas (str): Performativas aceites. Sem nenhuma, aceita todas.
        thread (str | None): Se indicado, só mensagens desta conversa.

    Returns:
        spade.template.Template: O filtro pronto a usar.

    Raises:
        ValueError: Se o protocolo ou uma performativa não existirem.
    """
    if protocolo not in PROTOCOLOS:
        raise ValueError(f"protocolo desconhecido: {protocolo!r}")
    for p in performativas:
        if p not in PERFORMATIVAS:
            raise ValueError(f"performativa desconhecida: {p!r}")

    from spade.template import Template

    def um(performativa):
        """Template de um só protocolo, com uma performativa e o thread, se houver."""
        t = Template()
        t.set_metadata("protocol", protocolo)
        if performativa:
            t.set_metadata("performative", performativa)
        if thread is not None:
            t.thread = thread
        return t

    resultado = um(performativas[0] if performativas else None)
    for p in performativas[1:]:
        resultado = resultado | um(p)      # OU entre templates (ver PDF do SPADE)
    return resultado
