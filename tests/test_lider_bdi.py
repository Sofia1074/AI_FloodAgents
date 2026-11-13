"""Testes da parte BDI do líder (lider.asl), sem servidor XMPP.

O teste liga as crenças à mão e faz avançar o interpretador do AgentSpeak,
como o behaviour BDI faria. As ações que enviam mensagens são trocadas por
gravadores. Precisa de spade e spade_bdi (o .venv do projeto tem).

Correr:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CAUDAL_ACEITE, RECURSOS_POR_RISCO  # noqa: E402

try:
    from agentes.lider import FICHEIRO_ASL, CommunityLeader, atomo
    TEM_BDI = True
except Exception:      # spade ou spade_bdi indisponíveis
    TEM_BDI = False


def novo_lider():
    """Líder sem arrancar, com as ações de envio trocadas por gravadores."""
    lider = CommunityLeader("liderA", "A")
    lider.pedidos = []
    lider.respostas = []
    lider.votos = []
    lider.pedir_mitigacao = lider.pedidos.append
    lider.responder = lambda *args: lider.respostas.append(args)
    lider.votar = lambda *args: lider.votos.append(args)
    return lider


def avancar(lider, passos=30):
    """Faz o que o behaviour BDI faz a cada volta: entrega as crenças novas
    ao interpretador e dá um passo."""
    for _ in range(passos):
        buffer = lider.bdi_intention_buffer
        while buffer:
            gatilho, tipo, termo, intencao = buffer.popleft()
            lider.bdi_agent.call(gatilho, tipo, termo, intencao)
        lider.bdi_agent.step()


@unittest.skipUnless(TEM_BDI, "spade_bdi não está disponível")
class TestLiderBDI(unittest.TestCase):

    def test_atomo_sem_acentos(self):
        self.assertEqual(atomo("crítico"), "critico")
        self.assertEqual(atomo("baixo"), "baixo")

    def test_risco_elevado_pede_os_recursos_do_config(self):
        lider = novo_lider()
        lider.bdi.set_belief("risco", "elevado")
        avancar(lider)
        self.assertEqual(lider.pedidos, [RECURSOS_POR_RISCO["elevado"]])

    def test_risco_baixo_nao_pede_nada(self):
        lider = novo_lider()
        lider.bdi.set_belief("risco", "moderado")
        avancar(lider)
        lider.bdi.set_belief("risco", "baixo")
        avancar(lider)
        self.assertEqual(len(lider.pedidos), 1)    # só o do risco moderado

    def test_proposta_que_cabe_e_aceite(self):
        lider = novo_lider()                       # risco baixo: aceita até 80
        lider.bdi.set_belief("proposta", 1, 40.0)
        avancar(lider)
        self.assertEqual(lider.respostas, [(1, "aceita", 40.0)])

    def test_proposta_acima_do_limite_gera_contraproposta(self):
        lider = novo_lider()
        lider.bdi.set_belief("risco", "elevado")   # aceita até 25
        lider.bdi.set_belief("proposta", 2, 60.0)
        avancar(lider)
        self.assertEqual(lider.respostas, [(2, "contraproposta", 25.0)])

    def test_risco_critico_rejeita_qualquer_descarga(self):
        lider = novo_lider()
        lider.bdi.set_belief("risco", "critico")
        lider.bdi.set_belief("proposta", 3, 10.0)
        avancar(lider)
        self.assertEqual(lider.respostas, [(3, "rejeita", 0.0)])

    def test_voto_sim_quando_o_caudal_cabe(self):
        lider = novo_lider()
        lider.bdi.set_belief("risco", "moderado")  # aceita até 50
        lider.bdi.set_belief("votacao", 1, 50.0)
        avancar(lider)
        self.assertEqual(lider.votos, [(1, "sim")])
        self.assertEqual(lider.respostas, [])      # votar não é responder à proposta

    def test_voto_nao_quando_nao_cabe_e_sem_contraproposta(self):
        lider = novo_lider()
        lider.bdi.set_belief("risco", "elevado")   # aceita até 25
        lider.bdi.set_belief("votacao", 2, 25.5)
        avancar(lider)
        self.assertEqual(lider.votos, [(2, "nao")])

    def test_risco_critico_vota_nao(self):
        lider = novo_lider()
        lider.bdi.set_belief("risco", "critico")
        lider.bdi.set_belief("votacao", 3, 10.0)
        avancar(lider)
        self.assertEqual(lider.votos, [(3, "nao")])

    def test_aviso_de_contingencia_fica_como_crenca(self):
        lider = novo_lider()
        lider.bdi.set_belief("contingencia", 60.0)
        avancar(lider)
        self.assertIn("contingencia", lider.bdi.get_belief("contingencia"))
        self.assertEqual(lider.votos, [])           # o líder só fica a saber

    def test_textos_do_asl_sem_acentos(self):
        """O spade_bdi lê o .asl com a codificação do sistema: um acento dentro
        de um texto entre aspas estraga-se e o plano falha ao imprimir."""
        with open(FICHEIRO_ASL, encoding="utf-8") as f:
            sem_comentarios = re.sub(r"//.*", "", f.read())
        for texto in re.findall(r'"[^"]*"', sem_comentarios):
            self.assertTrue(texto.isascii(), texto)

    def test_factos_do_asl_iguais_ao_config(self):
        """O .asl repete CAUDAL_ACEITE e RECURSOS_POR_RISCO: não podem divergir."""
        with open(FICHEIRO_ASL, encoding="utf-8") as f:
            asl = f.read()
        caudais = {r: float(v) for r, v in
                   re.findall(r"^caudal_aceite\((\w+), (\d+)\)\.", asl, re.M)}
        self.assertEqual(caudais, {atomo(r): v for r, v in CAUDAL_ACEITE.items()})
        recursos = {}
        for r, tipo, n in re.findall(r"^recurso\((\w+), (\w+), (\d+)\)\.", asl, re.M):
            recursos.setdefault(r, {})[tipo] = int(n)
        esperado = {atomo(r): v for r, v in RECURSOS_POR_RISCO.items() if v}
        self.assertEqual(recursos, esperado)


if __name__ == "__main__":
    unittest.main()
