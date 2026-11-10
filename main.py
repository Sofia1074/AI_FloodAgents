"""Ponto de entrada: cria os agentes, aplica o cenário e arranca.

Correr:  py -3.12 main.py
"""

import asyncio

import spade

from agentes import CommunityLeader, DamOperator, NeighbourhoodOperator
from cenarios import CENARIO_POR_OMISSAO, aplicar_cenario


async def main():
    barragem = DamOperator("barragem")
    operadores = [NeighbourhoodOperator(f"op{b}", b) for b in "ABC"]
    lideres = [CommunityLeader(f"lider{b}", b) for b in "ABC"]
    todos = [barragem, *operadores, *lideres]

    aplicar_cenario(CENARIO_POR_OMISSAO, barragem, operadores)

    for agente in todos:
        await agente.start(auto_register=True)
    print("7 agentes ativos", flush=True)

    await asyncio.sleep(60)

    for agente in todos:
        await agente.stop()


if __name__ == "__main__":
    spade.run(main(), embedded_xmpp_server=True)
