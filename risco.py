"""Classificação do risco de inundação de um bairro.

O operador do bairro usa estas regras (secção 3 do guia):

- O nível da água define a classe base (LIMITES_RISCO em config.py).
- Uma subida rápida do nível agrava o risco.
- Uma drenagem natural (sem bombas nem equipas) que não chega para a chuva
  atual agrava o risco: a água vai continuar a subir. Só conta a partir de
  NIVEL_MINIMO_DRENAGEM, para um bairro quase seco não ficar em alerta.
- Os agravantes somam no máximo AGRAVAMENTO_MAXIMO classes ao nível, para
  um bairro com pouca água não saltar logo para risco elevado.
"""

from config import (AGRAVAMENTO_MAXIMO, LIMIAR_SUBIDA_RAPIDA, LIMITES_RISCO,
                    NIVEL_MINIMO_DRENAGEM)

CLASSES = ["baixo", "moderado", "elevado", "crítico"]


def risco_pelo_nivel(nivel):
    """Classe de risco só pelo nível da água (0 a 100).

    Args:
        nivel: nível da água no bairro.
    Returns:
        "baixo", "moderado", "elevado" ou "crítico".
    """
    for limite, classe in LIMITES_RISCO:
        if nivel < limite:
            return classe
    return "crítico"


def classificar_risco(nivel, velocidade, entrada_chuva, drenagem):
    """Classe de risco com os agravantes do guia.

    Args:
        nivel: nível da água no bairro (0 a 100).
        velocidade: variação do nível no último ciclo (positiva = a subir).
        entrada_chuva: água que a chuva atual acrescenta por ciclo.
        drenagem: água que o bairro escoa por ciclo sem ajuda (drenagem natural).
    Returns:
        (classe, motivos): a classe de risco e a lista dos agravantes que
        a subiram ("subida rápida", "drenagem insuficiente").
    """
    motivos = []
    if velocidade >= LIMIAR_SUBIDA_RAPIDA:
        motivos.append("subida rápida")
    if nivel >= NIVEL_MINIMO_DRENAGEM and entrada_chuva > drenagem:
        motivos.append("drenagem insuficiente")
    base = CLASSES.index(risco_pelo_nivel(nivel))
    final = min(len(CLASSES) - 1, base + min(len(motivos), AGRAVAMENTO_MAXIMO))
    return CLASSES[final], motivos
