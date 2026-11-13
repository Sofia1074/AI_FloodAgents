"""Testes das regras da negociação da descarga (t07), sem servidor XMPP.

Correr:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agentes.barragem import (DamOperator, Negociacao, contar_favoraveis,
                                  em_ciclos, ha_maioria, reformular,
                                  resumo_respostas)
    from config import PERIODO_CICLO
    from spade.template import Template
    import mensagens
    TEM_SPADE = True
except Exception:      # spade indisponível
    TEM_SPADE = False

PLANO = {"caudal": 41.6, "atraso": 0, "duracao": 10}


def resposta(aceita, caudal=None, sem_resposta=False):
    """Resposta de um líder: aceita, ou rejeita (com contraproposta opcional)."""
    contra = dict(PLANO, caudal=caudal) if caudal is not None else None
    r = {"aceita": aceita, "contraproposta": contra}
    if sem_resposta:
        r["sem_resposta"] = True
    return r


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestMaioria(unittest.TestCase):

    def test_dois_em_tres_aprova(self):
        self.assertTrue(ha_maioria(2, 3))
        self.assertTrue(ha_maioria(3, 3))

    def test_um_em_tres_nao_aprova(self):
        self.assertFalse(ha_maioria(1, 3))
        self.assertFalse(ha_maioria(0, 3))

    def test_contar_favoraveis(self):
        respostas = {"lidera": resposta(True), "liderb": resposta(False),
                     "liderc": resposta(True)}
        self.assertEqual(contar_favoraveis(respostas), 2)


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestReformular(unittest.TestCase):

    def test_adota_a_contraproposta_mais_restritiva(self):
        respostas = {"lidera": resposta(False),                  # crítico: não contrapõe
                     "liderb": resposta(False, caudal=50.0),
                     "liderc": resposta(False, caudal=25.0)}
        novo = reformular(PLANO, respostas)
        self.assertEqual(novo["caudal"], 25.0)
        self.assertEqual((novo["atraso"], novo["duracao"]), (0, 10))

    def test_nao_altera_o_plano_original(self):
        reformular(PLANO, {"lidera": resposta(False, caudal=25.0)})
        self.assertEqual(PLANO["caudal"], 41.6)

    def test_sem_contrapropostas_nao_ha_novo_plano(self):
        respostas = {"lidera": resposta(False), "liderb": resposta(True)}
        self.assertIsNone(reformular(PLANO, respostas))

    def test_contraproposta_que_nao_baixa_o_caudal_nao_avanca(self):
        self.assertIsNone(reformular(PLANO, {"lidera": resposta(False, caudal=41.6)}))
        self.assertIsNone(reformular(PLANO, {"lidera": resposta(False, caudal=60.0)}))


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestResumoENegociacao(unittest.TestCase):

    def test_resumo_por_bairro(self):
        respostas = {"liderc": resposta(False, sem_resposta=True),
                     "lidera": resposta(False), "liderb": resposta(True)}
        self.assertEqual(resumo_respostas(respostas), "A:não B:sim C:sem resposta")

    def test_duracao_em_ciclos_e_segundos(self):
        self.assertEqual(em_ciclos(10), f"10 ciclos ({10 * PERIODO_CICLO} s)")

    def test_votacao_so_recebe_votos_da_sua_negociacao(self):
        class Ambiente:
            pass
        dam = DamOperator("barragem", Ambiente())
        dam.negociacao = Negociacao(thread="desc-001", plano=PLANO, lideres=["lidera"])
        _, template = dam.criar_votacao()
        voto = mensagens.criar("barragem", "accept-proposal", "votacao", "voto",
                               thread="desc-001")
        outra_negociacao = mensagens.criar("barragem", "accept-proposal", "votacao",
                                           "voto", thread="desc-002")
        resposta = mensagens.criar("barragem", "accept-proposal", "negociar-descarga",
                                   "resposta_proposta", thread="desc-001")
        self.assertTrue(template.match(voto))
        self.assertFalse(template.match(outra_negociacao))
        self.assertFalse(template.match(resposta))   # é do FSM, não da votação

    def test_complemento_do_template_vazio_nao_deixa_passar_nada(self):
        msg = mensagens.criar("barragem", "inform", "alerta-risco", "alerta")
        self.assertFalse((~Template()).match(msg))
        self.assertTrue(Template().match(msg))

    def test_id_da_proposta_acompanha_a_rodada(self):
        n = Negociacao(thread="desc-007", plano=PLANO, lideres=["lidera"])
        self.assertEqual(n.id_proposta, "desc-007-r1")
        n.rodada = 2
        self.assertEqual(n.id_proposta, "desc-007-r2")

    def test_fsm_tem_os_quatro_estados_do_guia(self):
        class Ambiente:                       # a barragem só guarda a referência
            pass
        dam = DamOperator("barragem", Ambiente())
        dam.negociacao = Negociacao(thread="desc-001", plano=PLANO, lideres=["lidera"])
        fsm, _ = dam.criar_negociacao()
        self.assertEqual(set(fsm.get_states()),
                         {"PROPOR", "AGUARDAR", "REFORMULAR", "ENCERRAR"})


if __name__ == "__main__":
    unittest.main()
