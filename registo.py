"""Saída no terminal: poucos eventos, com o tempo desde o início.

evento()  -> aparece sempre (o que mudou: alertas, votações, descargas...)
detalhe() -> só aparece com --verbose / -v (cada mensagem trocada)
"""

import time

_inicio = time.monotonic()
_verboso = False


def iniciar(verboso=False):
    """Começa a contar o tempo do terminal e escolhe se mostra os detalhes.

    Args:
        verboso (bool): Se True, `detalhe()` também escreve (opção -v).
    """
    global _inicio, _verboso
    _inicio = time.monotonic()
    _verboso = verboso


def evento(etiqueta, texto):
    """Escreve sempre uma linha de evento, com o tempo desde o início.

    Args:
        etiqueta (str): Tipo do evento, como "ALERTA", "VOTAÇÃO" ou "DESCARGA".
        texto (str): O que aconteceu, numa linha.
    """
    print(f"[t={time.monotonic() - _inicio:3.0f}s] {etiqueta:<10} {texto}",
          flush=True)


def detalhe(origem, texto):
    """Escreve uma linha de detalhe, só no modo verboso (-v).

    Args:
        origem (str): Quem escreve, como "liderA" ou "barragem".
        texto (str): O detalhe, numa linha.
    """
    if _verboso:
        print(f"        . [{origem}] {texto}", flush=True)
