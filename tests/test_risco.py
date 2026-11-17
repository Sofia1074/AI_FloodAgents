"""Testes da classificação de risco do bairro (sem SPADE).

Correr:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LIMIAR_SUBIDA_RAPIDA, NIVEL_MINIMO_DRENAGEM  # noqa: E402
from risco import descrever_tendencia  # noqa: E402


class TestTendencia(unittest.TestCase):

    def test_a_subir(self):
        self.assertEqual(descrever_tendencia(2.4), "a subir 2.4/ciclo")

    def test_a_descer_nao_diz_subir_com_sinal_negativo(self):
        texto = descrever_tendencia(-0.6)
        self.assertEqual(texto, "a descer 0.6/ciclo")
        self.assertNotIn("subir", texto)

    def test_quase_parado_e_estavel(self):
        self.assertEqual(descrever_tendencia(0.0), "estável")
        self.assertEqual(descrever_tendencia(-0.04), "estável")
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

    def test_drenagem_nao_agrava_se_o_nivel_ja_esta_a_descer(self):
        """Caso da simulação: bairro a 27, chuva maior que a drenagem natural,
        mas as bombas já fazem o nível descer: continua moderado."""
        dados = dict(CALMO, entrada_chuva=5.0, drenagem=2.0, velocidade=-0.6)
        classe, motivos = classificar_risco(nivel=27.0, **dados)
        self.assertEqual(classe, "moderado")
        self.assertNotIn("drenagem insuficiente", motivos)

    def test_drenagem_agrava_com_o_nivel_estavel(self):
        dados = dict(CALMO, entrada_chuva=5.0, drenagem=2.0, velocidade=0.0)
        classe, _ = classificar_risco(nivel=27.0, **dados)
        self.assertEqual(classe, "elevado")

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
