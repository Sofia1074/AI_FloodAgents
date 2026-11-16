"""Regras do mercado de serviços entre bairros (Contract Net, secção 5.3 do guia).

Só regras e contas, sem SPADE nem mensagens, para se poderem testar à parte.
Os agentes (agentes/contract_net.py e agentes/lider.py) usam estas funções
para decidir; o envio das mensagens fica com eles.

Regras organizacionais do modelo Gaia (docs/gaia_detalhado.md, 9.1.5):

- Regra 7 (reserva mínima): um Fornecedor só oferece um recurso se
  estoque - reservado - quantidade >= RESERVA_MINIMA. Além disso só oferece
  quando o seu bairro está em condições (risco em RISCOS_QUE_PERMITEM_OFERECER).
- Regra 8: um Comprador só aceita um preço que caiba na moeda disponível.
- Regra 9: o Comprador abre com cerca de 60% do preço base; o Fornecedor
  aceita a partir de 70% e contrapropõe abaixo disso.

Estratégia de concessão (escolha da equipa, dentro das regras do guia):

- O vendedor pede o preço base. Perante uma oferta abaixo de 70%, contrapõe
  o ponto médio entre o que pedia e a oferta, nunca abaixo de 70%.
- O comprador abre com 60%. Perante uma contraproposta, sobe para o ponto
  médio entre a sua última oferta e o preço pedido. Na última rodada aceita
  o preço pedido se não passar do preço base e couber na moeda.

Com o preço base 20 de uma bomba: vendedor pede 20, comprador oferece 12,
vendedor contrapõe 16, comprador oferece 14 (70%) e o vendedor aceita.
É um acordo bilateral (barganha), não um leilão: ver docs/materia.md.
"""

from config import (FRACAO_ABERTURA_COMPRADOR, FRACAO_MINIMA_VENDEDOR,
                    MAX_RODADAS_CN, PRECO_BASE, RESERVA_MINIMA,
                    RISCOS_QUE_PEDEM_CONTRATACAO, RISCOS_QUE_PERMITEM_OFERECER)

# decisões do comprador perante um preço do vendedor
ACEITAR = "aceitar"
CONTRAPROPOR = "contrapropor"
DESISTIR = "desistir"


def preco_base(servico):
    """Preço base de um serviço, por unidade.

    Args:
        servico (str): Por exemplo "bombas".

    Returns:
        float | None: O preço, ou None se o serviço não tiver preço.
    """
    return PRECO_BASE.get(servico)


def excedente(bairro, recurso, risco):
    """Unidades que o bairro pode vender sem violar a reserva mínima (regra 7).

    Args:
        bairro (ambiente.Bairro): Estado do bairro fornecedor.
        recurso (str): Recurso a avaliar.
        risco (str): Risco atual do bairro fornecedor.

    Returns:
        int: estoque - reservado - reserva mínima, ou 0 se o bairro não está
        em condições de vender ou o recurso não tem preço.
    """
    if risco not in RISCOS_QUE_PERMITEM_OFERECER or preco_base(recurso) is None:
        return 0
    return max(0, bairro.livre(recurso) - RESERVA_MINIMA.get(recurso, 0))


def pode_oferecer(bairro, recurso, quantidade, risco):
    """True se vender `quantidade` unidades respeita a regra 7.

    Args:
        bairro (ambiente.Bairro): Estado do bairro fornecedor.
        recurso (str): Recurso a vender.
        quantidade (int): Unidades a vender.
        risco (str): Risco atual do bairro fornecedor.

    Returns:
        bool: Se a venda deixa a reserva mínima intacta.
    """
    return 0 < quantidade <= excedente(bairro, recurso, risco)


def precisa_contratar(risco, falta):
    """Atividade IdentificarNecessidade do Comprador.

    Args:
        risco (str): Risco atual do bairro.
        falta (dict): Recursos que o estoque local não cobriu.

    Returns:
        bool: True se o risco é elevado ou crítico e falta alguma coisa.
    """
    return risco in RISCOS_QUE_PEDEM_CONTRATACAO and any(q > 0 for q in falta.values())


def arredondar(preco):
    """Arredonda um preço a duas casas (moeda fictícia)."""
    return round(float(preco), 2)


# ---- Vendedor (Fornecedor) --------------------------------------------------

def preco_minimo_vendedor(servico):
    """Menor preço por unidade que o vendedor aceita (70% do preço base)."""
    return arredondar(FRACAO_MINIMA_VENDEDOR * preco_base(servico))


def preco_pedido_inicial(servico):
    """Preço por unidade que o vendedor pede na primeira proposta (o preço base)."""
    return arredondar(preco_base(servico))


def vendedor_aceita(servico, preco):
    """Regra 9: o vendedor aceita a partir de 70% do preço base.

    Args:
        servico (str): Serviço negociado.
        preco (float): Preço por unidade oferecido pelo comprador.

    Returns:
        bool: Se o preço é aceite.
    """
    return preco >= preco_minimo_vendedor(servico) - 1e-9


def contraproposta_vendedor(servico, pedido_anterior, oferta):
    """Novo preço do vendedor quando recusa a oferta do comprador.

    Ponto médio entre o que pedia e a oferta, nunca abaixo de 70% do base.

    Args:
        servico (str): Serviço negociado.
        pedido_anterior (float): Preço que o vendedor pedia.
        oferta (float): Preço oferecido pelo comprador.

    Returns:
        float: O novo preço pedido, por unidade.
    """
    return arredondar(max(preco_minimo_vendedor(servico),
                          (pedido_anterior + oferta) / 2))


# ---- Comprador --------------------------------------------------------------

def oferta_inicial_comprador(servico):
    """Primeira oferta do comprador: 60% do preço base, por unidade."""
    return arredondar(FRACAO_ABERTURA_COMPRADOR * preco_base(servico))


def decisao_comprador(servico, preco_pedido, quantidade, moeda_disponivel,
                      rodada, ultima_oferta=None, max_rodadas=MAX_RODADAS_CN):
    """O que o comprador faz perante o preço pedido pelo vendedor.

    Args:
        servico (str): Serviço negociado.
        preco_pedido (float): Preço por unidade pedido pelo vendedor.
        quantidade (int): Unidades propostas.
        moeda_disponivel (float): Moeda do bairro ainda não comprometida.
        rodada (int): Rodada atual, a começar em 1.
        ultima_oferta (float | None): Última oferta do comprador (None na
            primeira rodada).
        max_rodadas (int): Rodadas permitidas.

    Returns:
        tuple: (decisão, preço por unidade). A decisão é ACEITAR (ao preço
        pedido), CONTRAPROPOR (com o preço devolvido) ou DESISTIR.
    """
    base = preco_base(servico)
    cabe = preco_pedido * quantidade <= moeda_disponivel + 1e-9     # regra 8
    abertura = oferta_inicial_comprador(servico)

    if cabe and preco_pedido <= abertura + 1e-9:
        return ACEITAR, arredondar(preco_pedido)        # já é barato: aceita
    if rodada >= max_rodadas:
        if cabe and preco_pedido <= base + 1e-9:
            return ACEITAR, arredondar(preco_pedido)
        return DESISTIR, None
    if ultima_oferta is None:
        oferta = abertura                               # regra 9: abre com 60%
    else:
        oferta = arredondar((ultima_oferta + preco_pedido) / 2)
    if oferta * quantidade > moeda_disponivel + 1e-9:
        # nem a oferta cabe: oferece só o que a moeda permite, se der algo
        oferta = arredondar(moeda_disponivel / quantidade) if quantidade else 0.0
        if oferta <= 0 or oferta <= (ultima_oferta or 0):
            return DESISTIR, None
    return CONTRAPROPOR, oferta
