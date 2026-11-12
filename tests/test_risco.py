"""Testes da classificação de risco do bairro (sem SPADE).

Correr:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LIMIAR_SUBIDA_RAPIDA, NIVEL_MINIMO_DRENAGEM  # noqa: E402
from risco import classificar_risco, risco_pelo_nivel  # noqa: E402

CALMO = {"velocidade": 0.0, "entrada_chuva": 0.0, "drenagem": 2.0}


class TestRiscoPeloNivel(unittest.TestCase):

    def test_limites_do_nivel(self):
        self.assertEqual(risco_pelo_nivel(10), "baixo")
        self.assertEqual(risco_pelo_nivel(30), "moderado")
        self.assertEqual(risco_pelo_nivel(60), "elevado")
        self.assertEqual(risco_pelo_nivel(80), "crítico")

    def test_valores_na_fronteira_sobem_de_classe(self):
        self.assertEqual(risco_pelo_nivel(25), "moderado")
        self.assertEqual(risco_pelo_nivel(75), "crítico")


class TestClassificarRisco(unittest.TestCase):

    def test_sem_agravantes_vale_o_nivel(self):
        risco, motivos = classificar_risco(30, **CALMO)
        self.assertEqual(risco, "moderado")
        self.assertEqual(motivos, [])

    def test_subida_rapida_agrava_uma_classe(self):
        dados = dict(CALMO, velocidade=LIMIAR_SUBIDA_RAPIDA)
        risco, motivos = classificar_risco(30, **dados)
        self.assertEqual(risco, "elevado")
        self.assertIn("subida rápida", motivos)

    def test_drenagem_insuficiente_agrava_uma_classe(self):
        dados = dict(CALMO, entrada_chuva=5.0, drenagem=2.0)
        risco, motivos = classificar_risco(20, **dados)
        self.assertEqual(risco, "moderado")
        self.assertIn("drenagem insuficiente", motivos)

    def test_drenagem_nao_agrava_com_pouca_agua(self):
        dados = dict(CALMO, entrada_chuva=5.0, drenagem=2.0)
        risco, motivos = classificar_risco(NIVEL_MINIMO_DRENAGEM - 1, **dados)
        self.assertEqual(risco, "baixo")
        self.assertEqual(motivos, [])

    def test_dois_agravantes_sobem_no_maximo_uma_classe(self):
        dados = {"velocidade": 6.0, "entrada_chuva": 5.0, "drenagem": 2.0}
        risco, motivos = classificar_risco(20, **dados)
        self.assertEqual(risco, "moderado")
        self.assertEqual(len(motivos), 2)

    def test_critico_nao_passa_de_critico(self):
        dados = {"velocidade": 6.0, "entrada_chuva": 5.0, "drenagem": 2.0}
        risco, _ = classificar_risco(90, **dados)
        self.assertEqual(risco, "crítico")

    def test_agua_a_descer_nao_agrava(self):
        dados = dict(CALMO, velocidade=-5.0)
        risco, motivos = classificar_risco(30, **dados)
        self.assertEqual(risco, "moderado")
        self.assertEqual(motivos, [])


if __name__ == "__main__":
    unittest.main()
