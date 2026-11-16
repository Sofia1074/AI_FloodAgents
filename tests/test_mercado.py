"""Testes do estoque, da rede e das regras do mercado (t11, t12, t13), sem SPADE.

Correr:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mercado  # noqa: E402
from ambiente import Bairro  # noqa: E402
from config import MAX_RODADAS_CN, PRECO_BASE, RESERVA_MINIMA  # noqa: E402
from rede import REDE  # noqa: E402


def bairro(**estoque):
    """Bairro com o estoque indicado e moeda 100."""
    return Bairro(nome="A", estoque=dict(estoque), moeda=100.0)


class TestEstoque(unittest.TestCase):
    """Regras do ExecutorLocal: estoque >= 0 e reservado <= estoque."""

    def test_separar_pedido_divide_o_que_ha_e_o_que_falta(self):
        b = bairro(bombas=1, barreiras=2)
        ativar, falta = b.separar_pedido({"bombas": 3, "barreiras": 1, "equipas": 1})
        self.assertEqual(ativar, {"bombas": 1, "barreiras": 1})
        self.assertEqual(falta, {"bombas": 2, "equipas": 1})

    def test_gastar_e_tudo_ou_nada(self):
        b = bairro(bombas=1, barreiras=1)
        self.assertFalse(b.gastar({"bombas": 1, "barreiras": 2}))
        self.assertEqual(b.estoque, {"bombas": 1, "barreiras": 1})
        self.assertTrue(b.gastar({"bombas": 1}))
        self.assertEqual(b.estoque["bombas"], 0)

    def test_reserva_nao_se_usa_na_mitigacao(self):
        b = bairro(bombas=3)
        self.assertTrue(b.reservar("bombas", 2))
        self.assertEqual(b.livre("bombas"), 1)
        ativar, falta = b.separar_pedido({"bombas": 2})
        self.assertEqual((ativar, falta), ({"bombas": 1}, {"bombas": 1}))
        self.assertFalse(b.gastar({"bombas": 2}))

    def test_nao_reserva_mais_do_que_o_livre(self):
        b = bairro(bombas=2)
        self.assertFalse(b.reservar("bombas", 3))
        self.assertTrue(b.reservar("bombas", 2))
        self.assertFalse(b.reservar("bombas", 1))
        self.assertLessEqual(b.reservado["bombas"], b.estoque["bombas"])

    def test_gastar_reserva_e_libertar(self):
        b = bairro(bombas=3)
        b.reservar("bombas", 2)
        self.assertTrue(b.gastar_reserva("bombas", 2))
        self.assertEqual((b.estoque["bombas"], b.reservado["bombas"]), (1, 0))
        self.assertFalse(b.gastar_reserva("bombas", 1))      # já não há reserva
        b.reservar("bombas", 1)
        b.libertar("bombas", 1)
        self.assertEqual((b.livre("bombas"), b.reservado["bombas"]), (1, 0))


class TestReservaMinima(unittest.TestCase):
    """Regra 7 e "condições adequadas" para oferecer."""

    def test_excedente_desconta_reserva_minima_e_reservas(self):
        b = bairro(bombas=3)
        self.assertEqual(mercado.excedente(b, "bombas", "baixo"),
                         3 - RESERVA_MINIMA["bombas"])
        b.reservar("bombas", 1)
        self.assertEqual(mercado.excedente(b, "bombas", "baixo"),
                         2 - RESERVA_MINIMA["bombas"])

    def test_nao_oferece_abaixo_da_reserva_minima(self):
        b = bairro(equipas=RESERVA_MINIMA["equipas"])
        self.assertEqual(mercado.excedente(b, "equipas", "baixo"), 0)
        self.assertFalse(mercado.pode_oferecer(b, "equipas", 1, "baixo"))

    def test_bairro_em_risco_alto_nao_oferece(self):
        b = bairro(bombas=5)
        self.assertGreater(mercado.excedente(b, "bombas", "moderado"), 0)
        self.assertEqual(mercado.excedente(b, "bombas", "elevado"), 0)
        self.assertEqual(mercado.excedente(b, "bombas", "crítico"), 0)

    def test_precisa_contratar_so_com_risco_alto_e_falta(self):
        self.assertTrue(mercado.precisa_contratar("elevado", {"bombas": 1}))
        self.assertTrue(mercado.precisa_contratar("crítico", {"bombas": 1}))
        self.assertFalse(mercado.precisa_contratar("moderado", {"bombas": 1}))
        self.assertFalse(mercado.precisa_contratar("elevado", {}))


class TestPrecos(unittest.TestCase):
    """Regras 8 e 9: preço de abertura, mínimo do vendedor e moeda."""

    def test_abertura_e_minimo(self):
        self.assertEqual(mercado.oferta_inicial_comprador("bombas"), 12.0)
        self.assertEqual(mercado.preco_minimo_vendedor("bombas"), 14.0)
        self.assertFalse(mercado.vendedor_aceita("bombas", 13.99))
        self.assertTrue(mercado.vendedor_aceita("bombas", 14.0))

    def test_contraproposta_do_vendedor_nunca_abaixo_de_70(self):
        self.assertEqual(mercado.contraproposta_vendedor("bombas", 20.0, 12.0), 16.0)
        self.assertEqual(mercado.contraproposta_vendedor("bombas", 14.5, 6.0), 14.0)

    def test_negociacao_completa_fecha_a_70_por_cento(self):
        """Simula as rodadas: 20 -> oferta 12 -> 16 -> oferta 14 -> aceite."""
        for servico, base in PRECO_BASE.items():
            pedido, oferta, rodada = mercado.preco_pedido_inicial(servico), None, 1
            while True:
                decisao, preco = mercado.decisao_comprador(
                    servico, pedido, 1, 1000.0, rodada, oferta)
                if decisao != mercado.CONTRAPROPOR:
                    break
                oferta = preco
                if mercado.vendedor_aceita(servico, oferta):
                    break
                pedido = mercado.contraproposta_vendedor(servico, pedido, oferta)
                rodada += 1
            self.assertEqual(decisao, mercado.CONTRAPROPOR, servico)
            self.assertAlmostEqual(oferta, 0.7 * base, places=2, msg=servico)
            self.assertLessEqual(rodada, MAX_RODADAS_CN)

    def test_comprador_nao_aceita_o_que_nao_pode_pagar(self):
        decisao, _ = mercado.decisao_comprador("bombas", 20.0, 2, 30.0,
                                               rodada=MAX_RODADAS_CN, ultima_oferta=14.0)
        self.assertEqual(decisao, mercado.DESISTIR)

    def test_comprador_aceita_logo_um_preco_baixo(self):
        decisao, preco = mercado.decisao_comprador("bombas", 11.0, 1, 100.0, rodada=1)
        self.assertEqual((decisao, preco), (mercado.ACEITAR, 11.0))

    def test_ultima_rodada_aceita_ate_ao_preco_base(self):
        decisao, _ = mercado.decisao_comprador("bombas", 18.0, 1, 100.0,
                                               rodada=MAX_RODADAS_CN, ultima_oferta=14.0)
        self.assertEqual(decisao, mercado.ACEITAR)
        decisao, _ = mercado.decisao_comprador("bombas", 25.0, 1, 100.0,
                                               rodada=MAX_RODADAS_CN, ultima_oferta=14.0)
        self.assertEqual(decisao, mercado.DESISTIR)


class TestRede(unittest.TestCase):
    """t13: ligações líder <-> líder e líder <-> diretório."""

    def test_lideres_falam_todos_com_todos(self):
        for a in "ABC":
            for b in "ABC":
                if a != b:
                    self.assertTrue(REDE.pode_comunicar(f"lider{a}", f"lider{b}"))

    def test_lideres_e_diretorio(self):
        for b in "ABC":
            self.assertTrue(REDE.pode_comunicar(f"lider{b}", "diretorio"))
            self.assertTrue(REDE.pode_comunicar("diretorio", f"lider{b}"))

    def test_diretorio_nao_fala_com_operadores_nem_barragem(self):
        for outro in ("opA", "opB", "opC", "barragem"):
            self.assertFalse(REDE.pode_comunicar("diretorio", outro))
            self.assertFalse(REDE.pode_comunicar(outro, "diretorio"))

    def test_operador_nao_fala_com_lider_de_outro_bairro(self):
        self.assertFalse(REDE.pode_comunicar("opA", "liderB"))

    def test_nomes_em_minusculas_do_jid(self):
        self.assertTrue(REDE.pode_comunicar("lidera", "liderb"))


if __name__ == "__main__":
    unittest.main()
