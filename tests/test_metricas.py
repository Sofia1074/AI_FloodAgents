"""Testes da recolha de métricas (sem SPADE).

Correr:  python -m unittest discover -s tests -v
"""

import asyncio
import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import metricas  # noqa: E402
from ambiente import Ambiente  # noqa: E402
from cenarios import CENARIOS  # noqa: E402
from metricas import Recolha  # noqa: E402


def recolha(cenario="risco_elevado"):
    amb = Ambiente(CENARIOS[cenario])
    return Recolha(cenario, amb), amb


def avancar(rec, amb, ciclos):
    for _ in range(ciclos):
        amb.passo()
        rec.registar_ciclo()


class TestCiclos(unittest.TestCase):

    def test_cada_ciclo_fica_registado_com_os_bairros(self):
        rec, amb = recolha()
        avancar(rec, amb, 3)
        self.assertEqual(len(rec.ciclos), 3)
        linha = rec.ciclos[-1]
        self.assertEqual(linha["ciclo"], 3)
        for b in "ABC":
            self.assertIn(f"nivel_{b}", linha)
            self.assertIn(f"risco_{b}", linha)
            self.assertIn(f"velocidade_{b}", linha)

    def test_risco_real_guarda_o_primeiro_ciclo_elevado(self):
        rec, amb = recolha()
        avancar(rec, amb, 15)
        self.assertIn("A", rec.inicio_risco_real)
        ciclo = rec.inicio_risco_real["A"]
        self.assertIn(rec.ciclos[ciclo - 1]["risco_A"], ("elevado", "crítico"))


class TestEventos(unittest.TestCase):

    def test_tempo_de_deteccao_em_ciclos(self):
        rec, amb = recolha()
        while "A" not in rec.inicio_risco_real:
            avancar(rec, amb, 1)
        inicio = rec.inicio_risco_real["A"]
        avancar(rec, amb, 2)
        rec.alerta("A", "elevado")
        self.assertEqual(rec.resumo()["tempo_deteccao_ciclos"]["A"], amb.ciclo - inicio)

    def test_alerta_antes_do_risco_real_nao_conta_como_deteccao(self):
        rec, amb = recolha()
        rec.alerta("A", "elevado")          # ciclo 0, antes de o risco começar
        avancar(rec, amb, 15)
        self.assertIsNone(rec.resumo()["tempo_deteccao_ciclos"]["A"])

    def test_bairro_que_nunca_chega_a_elevado_nao_tem_tempo(self):
        rec, amb = recolha("calmo")
        avancar(rec, amb, 5)
        rec.alerta("A", "moderado")
        self.assertIsNone(rec.resumo()["tempo_deteccao_ciclos"]["A"])

    def test_propostas_votacoes_e_rejeicoes(self):
        rec, _ = recolha("conflito")
        rec.proposta(40.0)
        rec.decisao(aprovado=True, favoraveis=2, total=3)
        rec.descarga(40.0, 10)
        rec.proposta(70.0)
        rec.decisao(aprovado=False, favoraveis=1, total=3)
        rec.rejeitada_seguranca("caudal acima do máximo seguro")
        r = rec.resumo()["propostas"]
        self.assertEqual(r, {"total": 2, "aprovadas": 1, "rejeitadas_votacao": 1,
                             "rejeitadas_seguranca": 1, "descargas": 1})
        self.assertEqual(len(rec.resumo()["tempo_ate_decisao_s"]), 2)
        self.assertTrue(all(t >= 0 for t in rec.resumo()["tempo_ate_decisao_s"]))

    def test_recursos_usados_por_bairro_e_total(self):
        rec, _ = recolha()
        rec.mitigacao("A", {"bombas": 2, "barreiras": 1})
        rec.mitigacao("A", {"bombas": 1})
        rec.mitigacao("B", {"equipas": 1})
        r = rec.resumo()["recursos"]
        self.assertEqual(r["por_bairro"]["A"], {"bombas": 3, "barreiras": 1})
        self.assertEqual(r["total"], {"bombas": 3, "barreiras": 1, "equipas": 1})

    def test_transacoes_e_precos(self):
        rec, _ = recolha("recursos_limitados")
        rec.transacao("B", "A", "bombas", 1, 14.0)
        rec.transacao("B", "C", "bombas", 1, 16.0)
        r = rec.resumo()["transacoes"]
        self.assertEqual(r["total"], 2)
        self.assertAlmostEqual(r["preco_medio"]["bombas"], 15.0)

    def test_mensagens_por_performativa(self):
        rec, _ = recolha()
        rec.mensagem("opA", "inform")
        rec.mensagem("barragem", "propose")
        rec.mensagem("barragem", "propose")
        r = rec.resumo()["mensagens"]
        self.assertEqual(r["total"], 3)
        self.assertEqual(r["por_performativa"]["propose"], 2)


class TestResumoEExportacao(unittest.TestCase):

    def test_pico_e_ciclos_em_risco(self):
        rec, amb = recolha()
        avancar(rec, amb, 15)
        r = rec.resumo()
        self.assertGreater(r["nivel_maximo"]["A"], r["nivel_maximo"]["C"])
        self.assertGreater(r["ciclos_em_risco_elevado"]["A"], 0)

    def test_exportar_escreve_os_tres_ficheiros(self):
        rec, amb = recolha()
        avancar(rec, amb, 4)
        rec.alerta("A", "moderado")
        with tempfile.TemporaryDirectory() as pasta:
            rec.exportar(pasta)
            with open(os.path.join(pasta, "ciclos.csv"), encoding="utf-8") as f:
                linhas = list(csv.DictReader(f))
            self.assertEqual(len(linhas), 4)
            self.assertIn("nivel_A", linhas[0])
            with open(os.path.join(pasta, "eventos.csv"), encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 1)
            with open(os.path.join(pasta, "resumo.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["cenario"], "risco_elevado")


class TestFuncoesDoModulo(unittest.TestCase):

    def tearDown(self):
        metricas.terminar()

    def test_ganchos_nao_fazem_nada_sem_iniciar(self):
        metricas.terminar()
        metricas.alerta("A", "elevado")
        metricas.mitigacao("A", {"bombas": 1})
        metricas.registar_ciclo()
        self.assertIsNone(metricas.atual())

    def test_ganchos_vao_para_a_recolha_iniciada(self):
        amb = Ambiente(CENARIOS["calmo"])
        metricas.iniciar("calmo", amb)
        metricas.mitigacao("B", {"bombas": 2})
        self.assertEqual(metricas.atual().resumo()["recursos"]["total"], {"bombas": 2})

    def test_contador_de_mensagens_numa_classe_de_behaviour(self):
        class Mensagem:
            def get_metadata(self, chave):
                return "inform" if chave == "performative" else None

        class Agente:
            name = "opA"

        class Behaviour:
            agent = Agente()
            enviadas = 0

            async def send(self, msg):
                Behaviour.enviadas += 1

        metricas.iniciar("calmo", Ambiente(CENARIOS["calmo"]))
        metricas.instalar_contador_mensagens(Behaviour)
        metricas.instalar_contador_mensagens(Behaviour)   # duas vezes não conta a dobrar
        asyncio.run(Behaviour().send(Mensagem()))
        self.assertEqual(Behaviour.enviadas, 1)
        self.assertEqual(metricas.atual().resumo()["mensagens"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
