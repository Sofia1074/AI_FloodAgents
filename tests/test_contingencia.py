"""Testes da validação depois do voto e da contingência da barragem (t09),
sem servidor XMPP: o ambiente e o envio de mensagens são trocados por falsos.

Correr:  python -m unittest discover -s tests -v
"""

import asyncio
import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agentes.barragem import (DamOperator, Negociacao, Votacao,
                                  executar_contingencia)
    from config import (NIVEL_ALERTA_RESERVATORIO, NIVEL_CONTINGENCIA_RESERVATORIO,
                        NIVEL_EMERGENCIA_RESERVATORIO)
    TEM_SPADE = True
except Exception:      # spade indisponível
    TEM_SPADE = False

PLANO = {"caudal": 40.0, "atraso": 0, "duracao": 10}


class AmbienteFalso:
    """O que a barragem usa do ambiente: nível, descarga ativa e abrir comportas."""

    def __init__(self, nivel, ativa=False):
        self.nivel_reservatorio = nivel
        self.ativa = ativa
        self.descargas = []

    def descarga_ativa(self):
        return self.ativa

    def iniciar_descarga(self, caudal, duracao, atraso=0):
        self.descargas.append((caudal, duracao, atraso))


def barragem(nivel, ativa=False):
    return DamOperator("barragem", AmbienteFalso(nivel, ativa))


class ComportamentoFalso:
    """Faz de behaviour: tem o agente e guarda as mensagens que enviaria."""

    def __init__(self, dam):
        self.agent = dam
        self.enviadas = []

    async def send(self, msg):
        self.enviadas.append(msg)


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestValidacao(unittest.TestCase):

    def test_plano_seguro_e_aceite(self):
        self.assertEqual(barragem(88.0).validar_execucao(PLANO), (True, ""))

    def test_caudal_acima_do_maximo_seguro_e_recusado(self):
        dam = barragem(88.0)
        ok, razao = dam.validar_execucao(dict(PLANO, caudal=dam.caudal_maximo_seguro + 1))
        self.assertFalse(ok)
        self.assertIn("limites de segurança", razao)

    def test_nao_abre_com_outra_descarga_em_curso(self):
        ok, razao = barragem(88.0, ativa=True).validar_execucao(PLANO)
        self.assertFalse(ok)
        self.assertIn("em curso", razao)

    def test_nao_abre_se_o_reservatorio_ja_desceu_do_alerta(self):
        ok, razao = barragem(NIVEL_ALERTA_RESERVATORIO).validar_execucao(PLANO)
        self.assertFalse(ok)
        self.assertIn("nível de alerta", razao)


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestContingenciaRegras(unittest.TestCase):

    def test_plano_de_contingencia_respeita_o_maximo_seguro(self):
        dam = barragem(95.0)
        plano = dam.plano_contingencia()
        self.assertEqual(plano["caudal"], 60.0)          # 75% de 80
        self.assertTrue(dam.validar_plano(plano))

    def test_emergencia_so_a_partir_do_nivel_de_emergencia(self):
        self.assertFalse(barragem(NIVEL_EMERGENCIA_RESERVATORIO - 0.1).em_emergencia())
        self.assertTrue(barragem(NIVEL_EMERGENCIA_RESERVATORIO).em_emergencia())

    def test_sem_acordo_so_precisa_de_contingencia_com_reservatorio_alto(self):
        self.assertFalse(barragem(NIVEL_CONTINGENCIA_RESERVATORIO - 0.1).precisa_contingencia())
        self.assertTrue(barragem(NIVEL_CONTINGENCIA_RESERVATORIO).precisa_contingencia())
        self.assertFalse(barragem(95.0, ativa=True).precisa_contingencia())


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestExecutarContingencia(unittest.TestCase):

    def correr(self, dam, motivo="teste"):
        comportamento = ComportamentoFalso(dam)
        with contextlib.redirect_stdout(io.StringIO()):
            asyncio.run(executar_contingencia(comportamento, motivo))
        return comportamento.enviadas

    def test_abre_as_comportas_e_informa_lideres_e_operadores(self):
        dam = barragem(96.0)
        enviadas = self.correr(dam, "emergência")
        self.assertEqual(dam.ambiente.descargas, [(60.0, 10, 0)])
        self.assertEqual((dam.descargas, dam.contingencias), (1, 1))
        tipos = sorted(m.body.split('"tipo": "')[1].split('"')[0] for m in enviadas)
        self.assertEqual(tipos, ["aviso_contingencia"] * 3 + ["aviso_descarga"] * 3)

    def test_nao_aplica_com_outra_descarga_em_curso(self):
        dam = barragem(96.0, ativa=True)
        self.assertEqual(self.correr(dam), [])
        self.assertEqual((dam.ambiente.descargas, dam.contingencias), ([], 0))


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestDecidirDaVotacao(unittest.TestCase):
    """O que a votação faz com o resultado: executar, recusar ou contingência."""

    def decidir(self, nivel, votos_a_favor, ativa=False):
        dam = barragem(nivel, ativa)
        negociacao = Negociacao(thread="desc-001", plano=dict(PLANO),
                                lideres=["lidera", "liderb", "liderc"])
        votos = {f"lider{b}": {"aceita": i < votos_a_favor}
                 for i, b in enumerate("abc")}
        votacao = Votacao()
        votacao.agent = dam
        enviadas = []

        async def send(msg):
            enviadas.append(msg)
        votacao.send = send
        with contextlib.redirect_stdout(io.StringIO()):
            asyncio.run(votacao.decidir(negociacao, votos))
        return dam, enviadas

    def test_aprovado_e_seguro_executa_o_plano_votado(self):
        dam, _ = self.decidir(nivel=88.0, votos_a_favor=2)
        self.assertEqual(dam.ambiente.descargas, [(40.0, 10, 0)])
        self.assertEqual(dam.contingencias, 0)

    def test_aprovado_mas_inseguro_nao_executa(self):
        # o reservatório desceu do alerta durante a votação
        dam, _ = self.decidir(nivel=NIVEL_ALERTA_RESERVATORIO - 5, votos_a_favor=3)
        self.assertEqual(dam.ambiente.descargas, [])
        self.assertEqual(dam.contingencias, 0)

    def test_rejeitado_com_reservatorio_alto_aplica_a_contingencia(self):
        dam, _ = self.decidir(nivel=NIVEL_CONTINGENCIA_RESERVATORIO + 1, votos_a_favor=1)
        self.assertEqual(dam.ambiente.descargas, [(60.0, 10, 0)])   # não o plano votado
        self.assertEqual((dam.contingencias, dam.rejeitados), (1, 1))

    def test_rejeitado_com_reservatorio_baixo_espera(self):
        dam, _ = self.decidir(nivel=85.0, votos_a_favor=1)
        self.assertEqual(dam.ambiente.descargas, [])
        self.assertEqual((dam.contingencias, dam.rejeitados), (0, 1))


if __name__ == "__main__":
    unittest.main()
