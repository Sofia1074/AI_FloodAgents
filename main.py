"""Ponto de entrada: cria os agentes, aplica o cenário e arranca.

Correr:  py -3.12 main.py          (saída resumida: só os eventos)
         py -3.12 main.py -v       (mostra também cada mensagem trocada)
"""

import asyncio
import sys

import spade

import registo
from agentes import CommunityLeader, DamOperator, NeighbourhoodOperator
from cenarios import CENARIO_POR_OMISSAO, aplicar_cenario

DURACAO = 60   # segundos de simulação


def estado(barragem, operadores):
    bairros = "  ".join(f"{op.bairro}: {op.nivel_agua:.1f} ({op.avaliar_risco()})"
                        for op in operadores)
    return f"reservatório {barragem.nivel_reservatorio:.1f}% | {bairros}"


async def main(verboso):
    registo.iniciar(verboso)
    barragem = DamOperator("barragem")
    operadores = [NeighbourhoodOperator(f"op{b}", b) for b in "ABC"]
    lideres = [CommunityLeader(f"lider{b}", b) for b in "ABC"]
    aplicar_cenario(CENARIO_POR_OMISSAO, barragem, operadores)

    print(f"=== Cenário '{CENARIO_POR_OMISSAO}' | {DURACAO}s | "
          f"{'verboso' if verboso else 'resumido (use -v para ver as mensagens)'} ===",
          flush=True)
    print(f"Estado inicial: {estado(barragem, operadores)}", flush=True)

    # líderes antes dos operadores, para receberem os primeiros alertas
    todos = [*lideres, *operadores, barragem]
    for agente in todos:
        await agente.start(auto_register=True)
    registo.detalhe("main", "7 agentes ativos")

    await asyncio.sleep(DURACAO)

    for agente in todos:
        await agente.stop()

    print("=== Fim ===", flush=True)
    print(f"Estado final: {estado(barragem, operadores)}", flush=True)
    print(f"Descargas executadas: {barragem.descargas} | "
          f"planos rejeitados: {barragem.rejeitados}", flush=True)


if __name__ == "__main__":
    spade.run(main("-v" in sys.argv or "--verbose" in sys.argv),
              embedded_xmpp_server=True)
