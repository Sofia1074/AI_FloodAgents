"""Teste do arranque: o primeiro alerta chega ao líder mesmo que os operadores
arranquem antes dos líderes (t04). Usa o servidor XMPP embutido do SPADE.

Correr:  python -m unittest discover -s tests -v
(Não correr ao mesmo tempo que outra simulação: usam a mesma porta 5222.)
"""

import asyncio
import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import spade
    from agentes import CommunityLeader, NeighbourhoodOperator
    from ambiente import Ambiente
    from cenarios import CENARIOS
    TEM_SPADE = True
except Exception:      # spade ou spade_bdi indisponíveis
    TEM_SPADE = False


async def arrancar_operadores_primeiro(resultado):
    """Põe em `resultado` o risco que o líder A conhece 3 s depois do arranque
    (o spade.run não devolve o valor da corrotina)."""
    ambiente = Ambiente(CENARIOS["conflito"])          # o bairro A começa "elevado"
    operadores = [NeighbourhoodOperator(f"op{b}", b, ambiente) for b in "ABC"]
    lideres = [CommunityLeader(f"lider{b}", b) for b in "ABC"]
    agentes = [*operadores, *lideres]                  # ordem errada de propósito
    try:
        for agente in agentes:
            await agente.start(auto_register=True)
        for operador in operadores:
            operador.comecar()
        await asyncio.sleep(3)
        resultado.append(lideres[0].risco_do_bairro)
    finally:
        for agente in agentes:
            await agente.stop()


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestArranque(unittest.TestCase):

    def test_primeiro_alerta_chega_com_operadores_a_arrancar_primeiro(self):
        resultado = []
        with contextlib.redirect_stdout(io.StringIO()):     # esconde os eventos
            spade.run(arrancar_operadores_primeiro(resultado),
                      embedded_xmpp_server=True)
        self.assertEqual(resultado, ["elevado"])


if __name__ == "__main__":
    unittest.main()
