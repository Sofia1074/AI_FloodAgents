"""Testes do ambiente simulado (sem SPADE).

Correr:  py -3.12 -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ambiente import Ambiente  # noqa: E402
from cenarios import CENARIOS  # noqa: E402


def cenario_simples(**extra):
    """Cenário mínimo para os testes: sem chuva, tudo a zero."""
    base = {
        "reservatorio": 50.0,
        "chuva": [],
        "bairros": {
            b: {"nivel": 0.0, "humidade": 0.0, "drenagem": 2.0,
                "fator_chuva": 1.0, "exposicao": 0.1}
            for b in "ABC"
        },
    }
    base.update(extra)
    return base


class TestReservatorio(unittest.TestCase):

    def test_chuva_enche_o_reservatorio(self):
        amb = Ambiente(cenario_simples(chuva=[10.0] * 5))
        antes = amb.nivel_reservatorio
        for _ in range(5):
            amb.passo()
        self.assertGreater(amb.nivel_reservatorio, antes)

    def test_descarga_baixa_o_reservatorio_e_acaba_sozinha(self):
        amb = Ambiente(cenario_simples())
        amb.iniciar_descarga(caudal=60.0, duracao=3)
        antes = amb.nivel_reservatorio
        for _ in range(3):
            amb.passo()
        self.assertLess(amb.nivel_reservatorio, antes)
        amb.passo()
        self.assertEqual(amb.caudal_saida, 0.0)

    def test_nivel_do_reservatorio_fica_entre_0_e_100(self):
        amb = Ambiente(cenario_simples(reservatorio=99.0, chuva=[100.0] * 20))
        for _ in range(20):
            amb.passo()
        self.assertLessEqual(amb.nivel_reservatorio, 100.0)
        amb = Ambiente(cenario_simples(reservatorio=1.0))
        amb.iniciar_descarga(caudal=80.0, duracao=20)
        for _ in range(20):
            amb.passo()
        self.assertGreaterEqual(amb.nivel_reservatorio, 0.0)

    def test_descarga_sobe_o_nivel_a_jusante(self):
        amb = Ambiente(cenario_simples())
        amb.passo()
        sem_descarga = amb.nivel_jusante
        amb.iniciar_descarga(caudal=50.0, duracao=5)
        amb.passo()
        self.assertGreater(amb.nivel_jusante, sem_descarga)


class TestBairros(unittest.TestCase):

    def test_chuva_sobe_a_agua_e_calcula_velocidade(self):
        amb = Ambiente(cenario_simples(chuva=[10.0] * 3))
        amb.passo()
        a = amb.bairros["A"]
        self.assertGreater(a.nivel, 0.0)
        self.assertAlmostEqual(a.velocidade, a.nivel - 0.0)

    def test_drenagem_baixa_a_agua_sem_chuva(self):
        cen = cenario_simples()
        cen["bairros"]["A"]["nivel"] = 30.0
        amb = Ambiente(cen)
        amb.passo()
        self.assertLess(amb.bairros["A"].nivel, 30.0)
        self.assertLess(amb.bairros["A"].velocidade, 0.0)

    def test_bairro_mais_exposto_recebe_mais_agua_da_descarga(self):
        cen = cenario_simples()
        cen["bairros"]["A"]["exposicao"] = 0.2
        cen["bairros"]["C"]["exposicao"] = 0.05
        for b in "AC":
            cen["bairros"][b]["drenagem"] = 0.0
        amb = Ambiente(cen)
        amb.iniciar_descarga(caudal=50.0, duracao=5)
        amb.passo()
        self.assertGreater(amb.bairros["A"].nivel, amb.bairros["C"].nivel)

    def test_solo_encharcado_drena_pior(self):
        seco = cenario_simples()
        molhado = cenario_simples()
        for cen in (seco, molhado):
            cen["bairros"]["A"]["nivel"] = 30.0
        molhado["bairros"]["A"]["humidade"] = 1.0
        a_seco, a_molhado = Ambiente(seco), Ambiente(molhado)
        a_seco.passo()
        a_molhado.passo()
        self.assertGreater(a_molhado.bairros["A"].nivel, a_seco.bairros["A"].nivel)

    def test_guarda_a_chuva_do_ultimo_ciclo_e_a_entrada_no_bairro(self):
        amb = Ambiente(cenario_simples(chuva=[7.0, 3.0]))
        amb.passo()
        self.assertEqual(amb.chuva_ultimo_ciclo, 7.0)
        a = amb.bairros["A"]
        self.assertAlmostEqual(a.entrada_chuva(7.0), 7.0 * a.fator_chuva * (1.0 + a.humidade))

    def test_drenagem_natural_ignora_bombas(self):
        amb = Ambiente(cenario_simples())
        a = amb.bairros["A"]
        natural = a.drenagem_natural()
        amb.aplicar_mitigacao("A", {"bombas": 2})
        self.assertEqual(a.drenagem_natural(), natural)
        self.assertGreater(a.drenagem(), natural)

    def test_chuva_aumenta_a_humidade(self):
        amb = Ambiente(cenario_simples(chuva=[10.0] * 3))
        amb.passo()
        self.assertGreater(amb.bairros["A"].humidade, 0.0)

    def test_nivel_do_bairro_fica_entre_0_e_100(self):
        amb = Ambiente(cenario_simples(chuva=[100.0] * 30))
        for _ in range(30):
            amb.passo()
        for b in amb.bairros.values():
            self.assertLessEqual(b.nivel, 100.0)
            self.assertGreaterEqual(b.nivel, 0.0)


class TestMitigacao(unittest.TestCase):

    def test_bombas_baixam_a_agua_ao_longo_de_varios_ciclos(self):
        com = cenario_simples(chuva=[5.0] * 6)
        sem = cenario_simples(chuva=[5.0] * 6)
        a_com, a_sem = Ambiente(com), Ambiente(sem)
        a_com.aplicar_mitigacao("A", {"bombas": 2})
        for _ in range(4):
            a_com.passo()
            a_sem.passo()
        self.assertLess(a_com.bairros["A"].nivel, a_sem.bairros["A"].nivel)

    def test_barreiras_reduzem_a_agua_vinda_da_descarga(self):
        com, sem = cenario_simples(), cenario_simples()
        a_com, a_sem = Ambiente(com), Ambiente(sem)
        for amb in (a_com, a_sem):
            amb.iniciar_descarga(caudal=50.0, duracao=5)
        a_com.aplicar_mitigacao("A", {"barreiras": 1})
        a_com.passo()
        a_sem.passo()
        self.assertLess(a_com.bairros["A"].nivel, a_sem.bairros["A"].nivel)

    def test_efeito_dos_recursos_acaba(self):
        amb = Ambiente(cenario_simples())
        amb.aplicar_mitigacao("A", {"bombas": 1})
        for _ in range(50):
            amb.passo()
        self.assertEqual(amb.bairros["A"].efeitos, [])

    def test_recurso_desconhecido_nao_faz_nada(self):
        amb = Ambiente(cenario_simples())
        amb.aplicar_mitigacao("A", {"helicopteros": 3})
        self.assertEqual(amb.bairros["A"].efeitos, [])


class TestCenarios(unittest.TestCase):

    def test_todos_os_cenarios_criam_um_ambiente_valido(self):
        for nome, cen in CENARIOS.items():
            with self.subTest(cenario=nome):
                amb = Ambiente(cen)
                for _ in range(40):
                    amb.passo()
                self.assertEqual(set(amb.bairros), {"A", "B", "C"})

    def test_existem_os_tres_cenarios_do_guia(self):
        for nome in ("risco_elevado", "conflito", "recursos_limitados"):
            self.assertIn(nome, CENARIOS)

    def test_risco_elevado_tem_subida_rapida_num_bairro(self):
        amb = Ambiente(CENARIOS["risco_elevado"])
        maior = 0.0
        for _ in range(15):
            amb.passo()
            maior = max(maior, amb.bairros["A"].velocidade)
        self.assertGreater(maior, 3.0)

    def test_conflito_comeca_com_reservatorio_acima_do_alerta(self):
        from config import NIVEL_ALERTA_RESERVATORIO
        self.assertGreater(CENARIOS["conflito"]["reservatorio"],
                           NIVEL_ALERTA_RESERVATORIO)


if __name__ == "__main__":
    unittest.main()
