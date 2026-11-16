"""Testes do operador (estoque), do fornecedor no Contract Net e do plano
`falta` do líder, sem servidor XMPP.

Cria os agentes sem os arrancar e chama diretamente os métodos que tratam as
mensagens. Precisa de spade e spade_bdi (o .venv do projeto tem).

Correr:  python -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mensagens  # noqa: E402
from ambiente import Ambiente  # noqa: E402
from cenarios import CENARIOS  # noqa: E402

try:
    from agentes.lider import CommunityLeader
    from agentes.operador import NeighbourhoodOperator
    from tests.test_lider_bdi import avancar
    TEM_SPADE = True
except Exception:      # spade ou spade_bdi indisponíveis
    TEM_SPADE = False


def recebida(remetente, performativa, protocolo, tipo, thread="t-1", **corpo):
    """Mensagem já lida, como `mensagens.ler` a devolveria."""
    return mensagens.Recebida(remetente, performativa, protocolo, thread, tipo,
                              {"tipo": tipo, **corpo})


def resumo(msgs):
    """(destinatário, performativa, tipo) de cada mensagem SPADE."""
    return [(str(m.to).split("@")[0], m.get_metadata("performative"),
             json.loads(m.body)["tipo"]) for m in msgs]


def corpo(msg):
    """O corpo JSON de uma mensagem SPADE."""
    return json.loads(msg.body)


@unittest.skipUnless(TEM_SPADE, "spade não está disponível")
class TestOperadorEstoque(unittest.TestCase):
    """t11: AGREE ou REFUSE, depois INFORM ou FAILURE."""

    def setUp(self):
        self.amb = Ambiente(CENARIOS["recursos_limitados"])
        self.opA = NeighbourhoodOperator("opA", "A", self.amb)
        self.opB = NeighbourhoodOperator("opB", "B", self.amb)

    def pedido(self, recursos):
        return recebida("lidera", mensagens.REQUEST, mensagens.PEDIR_MITIGACAO,
                        "pedido_mitigacao", recursos=recursos)

    def test_sem_estoque_recusa_e_diz_o_que_falta(self):
        msgs = self.opB.tratar_pedido_mitigacao(self.pedido({"bombas": 2}))
        self.assertEqual(resumo(msgs), [("lidera", "refuse", "mitigacao_recusada")])
        self.assertEqual(corpo(msgs[0])["falta"], {"bombas": 2})

    def test_com_estoque_parcial_aceita_ativa_e_gasta(self):
        antes = self.amb.bairros["A"].estoque["bombas"]          # 3
        msgs = self.opA.tratar_pedido_mitigacao(self.pedido({"bombas": 5}))
        self.assertEqual(resumo(msgs), [("lidera", "agree", "mitigacao_aceite"),
                                        ("lidera", "inform", "mitigacao_ativada")])
        self.assertEqual(corpo(msgs[1])["recursos"], {"bombas": antes})
        self.assertEqual(corpo(msgs[1])["falta"], {"bombas": 5 - antes})
        self.assertEqual(self.amb.bairros["A"].estoque["bombas"], 0)
        self.assertEqual(len(self.amb.bairros["A"].efeitos), antes)

    def test_executar_servico_usa_a_reserva_no_bairro_comprador(self):
        self.amb.bairros["A"].reservar("bombas", 2)
        msgs = self.opA.tratar_execucao_servico(recebida(
            "lidera", mensagens.REQUEST, mensagens.EXECUTAR_SERVICO,
            "executar_servico", servico="bombas", quantidade=2, destino="B"))
        self.assertEqual([p for _, p, _ in resumo(msgs)], ["agree", "inform"])
        self.assertEqual(self.amb.bairros["A"].estoque["bombas"], 1)
        self.assertEqual(len(self.amb.bairros["B"].efeitos), 2)

    def test_executar_servico_sem_reserva_falha(self):
        msgs = self.opA.tratar_execucao_servico(recebida(
            "lidera", mensagens.REQUEST, mensagens.EXECUTAR_SERVICO,
            "executar_servico", servico="bombas", quantidade=1, destino="B"))
        self.assertEqual([p for _, p, _ in resumo(msgs)], ["agree", "failure"])
        self.assertEqual(self.amb.bairros["A"].estoque["bombas"], 3)


@unittest.skipUnless(TEM_SPADE, "spade não está disponível")
class TestFornecedor(unittest.TestCase):
    """t12: o lado do fornecedor (classe Vendas)."""

    def setUp(self):
        self.amb = Ambiente(CENARIOS["recursos_limitados"])
        self.liderA = CommunityLeader("liderA", "A", self.amb)
        self.vendas = self.liderA.vendas

    def cn(self, performativa, tipo, **dados):
        return self.vendas.tratar(recebida("liderb", performativa,
                                           mensagens.CONTRACT_NET, tipo, **dados))

    def test_cfp_propoe_so_o_excedente(self):
        msgs = self.cn(mensagens.CFP, "cfp", servico="bombas", quantidade=5)
        self.assertEqual(resumo(msgs), [("liderb", "propose", "proposta")])
        self.assertEqual(corpo(msgs[0])["quantidade"], 2)    # 3 - reserva mínima 1
        self.assertEqual(corpo(msgs[0])["preco"], 20.0)

    def test_cfp_sem_excedente_recusa(self):
        msgs = self.cn(mensagens.CFP, "cfp", servico="equipas", quantidade=1)
        self.assertEqual(resumo(msgs), [("liderb", "refuse", "recusa")])

    def test_cfp_com_risco_alto_recusa(self):
        self.liderA.risco_do_bairro = "elevado"
        msgs = self.cn(mensagens.CFP, "cfp", servico="bombas", quantidade=1)
        self.assertEqual(resumo(msgs), [("liderb", "refuse", "recusa")])

    def test_contraproposta_abaixo_de_70_e_contraposta(self):
        self.cn(mensagens.CFP, "cfp", servico="bombas", quantidade=1)
        msgs = self.cn(mensagens.PROPOSE, "contraproposta", preco=12.0, quantidade=1)
        self.assertEqual(resumo(msgs), [("liderb", "propose", "proposta")])
        self.assertEqual(corpo(msgs[0])["preco"], 16.0)
        self.assertEqual(self.amb.bairros["A"].reservado.get("bombas", 0), 0)

    def test_fluxo_completo_reserva_executa_confirma_e_recebe(self):
        self.cn(mensagens.CFP, "cfp", servico="bombas", quantidade=2)
        msgs = self.cn(mensagens.PROPOSE, "contraproposta", preco=14.0, quantidade=2)
        self.assertEqual(resumo(msgs)[:2], [("liderb", "accept-proposal", "aceitacao"),
                                            ("opa", "request", "executar_servico")])
        self.assertEqual(corpo(msgs[1])["destino"], "B")
        self.assertEqual(self.amb.bairros["A"].reservado["bombas"], 2)

        msgs = self.vendas.tratar(recebida("opa", mensagens.INFORM,
                                           mensagens.EXECUTAR_SERVICO,
                                           "servico_executado"))
        self.assertEqual(resumo(msgs), [("liderb", "inform", "servico_confirmado")])
        moeda = self.amb.bairros["A"].moeda
        self.cn(mensagens.INFORM, "pagamento", valor=28.0)
        self.assertEqual(self.amb.bairros["A"].moeda, moeda + 28.0)
        self.assertEqual(self.vendas.abertas, {})

    def test_falha_na_execucao_liberta_a_reserva_sem_pagamento(self):
        self.cn(mensagens.CFP, "cfp", servico="bombas", quantidade=1)
        self.cn(mensagens.ACCEPT_PROPOSAL, "aceitacao", preco=20.0, quantidade=1)
        self.assertEqual(self.amb.bairros["A"].reservado["bombas"], 1)
        msgs = self.vendas.tratar(recebida("opa", mensagens.FAILURE,
                                           mensagens.EXECUTAR_SERVICO, "servico_falhou",
                                           motivo="teste"))
        self.assertEqual(resumo(msgs)[0], ("liderb", "failure", "falha"))
        self.assertEqual(self.amb.bairros["A"].reservado["bombas"], 0)
        moeda = self.amb.bairros["A"].moeda
        self.cn(mensagens.INFORM, "pagamento", valor=20.0)     # não há venda aberta
        self.assertEqual(self.amb.bairros["A"].moeda, moeda)

    def test_pagamento_antes_da_confirmacao_e_ignorado(self):
        self.cn(mensagens.CFP, "cfp", servico="bombas", quantidade=1)
        self.cn(mensagens.ACCEPT_PROPOSAL, "aceitacao", preco=20.0, quantidade=1)
        moeda = self.amb.bairros["A"].moeda
        self.cn(mensagens.INFORM, "pagamento", valor=20.0)
        self.assertEqual(self.amb.bairros["A"].moeda, moeda)

    def test_ignora_mensagens_de_threads_desconhecidos(self):
        self.assertEqual(self.cn(mensagens.PROPOSE, "proposta", preco=10.0), [])

    def test_ofertas_so_publicam_quando_mudam(self):
        primeiras = resumo(self.liderA.mensagens_ofertas())
        self.assertTrue(primeiras)
        self.assertEqual(self.liderA.mensagens_ofertas(), [])
        self.liderA.risco_do_bairro = "elevado"
        zeradas = self.liderA.mensagens_ofertas()
        self.assertTrue(all(corpo(m)["quantidade"] == 0 for m in zeradas))


@unittest.skipUnless(TEM_SPADE, "spade_bdi não está disponível")
class TestPlanoFalta(unittest.TestCase):
    """t12: o lider.asl só contrata com risco elevado ou crítico."""

    def novo(self):
        lider = CommunityLeader("liderB", "B")
        lider.contratos = []
        lider.pedir_mitigacao = lambda *a: None
        lider.contratar = lambda recurso, qtd: lider.contratos.append((recurso, qtd))
        return lider

    def test_risco_elevado_contrata_o_que_falta(self):
        lider = self.novo()
        lider.bdi.set_belief("risco", "elevado")
        avancar(lider)
        lider.registar_falta({"bombas": 2, "barreiras": 1})
        avancar(lider)
        self.assertCountEqual(lider.contratos, [("bombas", 2), ("barreiras", 1)])

    def test_risco_critico_contrata(self):
        lider = self.novo()
        lider.bdi.set_belief("risco", "critico")
        avancar(lider)
        lider.registar_falta({"equipas": 1})
        avancar(lider)
        self.assertEqual(lider.contratos, [("equipas", 1)])

    def test_risco_moderado_nao_contrata(self):
        lider = self.novo()
        lider.bdi.set_belief("risco", "moderado")
        avancar(lider)
        lider.registar_falta({"bombas": 1})
        avancar(lider)
        self.assertEqual(lider.contratos, [])

    def test_falta_repetida_volta_a_disparar(self):
        lider = self.novo()
        lider.bdi.set_belief("risco", "elevado")
        avancar(lider)
        lider.registar_falta({"bombas": 1})
        avancar(lider)
        lider.registar_falta({"bombas": 1})
        avancar(lider)
        self.assertEqual(lider.contratos, [("bombas", 1), ("bombas", 1)])


if __name__ == "__main__":
    unittest.main()
