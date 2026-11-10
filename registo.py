"""Saída no terminal: poucos eventos, com o tempo desde o início.

evento()  -> aparece sempre (o que mudou: alertas, votações, descargas...)
detalhe() -> só aparece com --verbose / -v (cada mensagem trocada)
"""

import time

_inicio = time.monotonic()
_verboso = False


def iniciar(verboso=False):
    global _inicio, _verboso
    _inicio = time.monotonic()
    _verboso = verboso


def evento(etiqueta, texto):
    print(f"[t={time.monotonic() - _inicio:3.0f}s] {etiqueta:<10} {texto}",
          flush=True)


def detalhe(origem, texto):
    if _verboso:
        print(f"        . [{origem}] {texto}", flush=True)
