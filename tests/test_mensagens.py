"""Testes do mensagens.py. A parte que usa o SPADE só corre se ele estiver instalado.

Correr:  python -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mensagens  # noqa: E402

try:
    import spade.message  # noqa: F401
    TEM_SPADE = True
except Exception:      # não instalado, ou instalado mas avariado
    TEM_SPADE = False


def falsa(corpo, performativa="propose", protocolo="negociar-descarga",
          thread="desc-001", remetente="barragem"):
    """Imita uma mensagem recebida, sem precisar do SPADE."""
    meta = {"performative": performativa, "protocol": protocolo}
    return SimpleNamespace(body=corpo, thread=thread,
                           sender=SimpleNamespace(user=remetente),
                           get_metadata=meta.get)


class TestCorpo(unittest.TestCase):

    def test_ida_e_volta(self):
        texto = mensagens.montar_corpo("proposta_descarga", {"caudal": 40.0})
        self.assertEqual(mensagens.interpretar_corpo(texto),
                         {"tipo": "proposta_descarga", "caudal": 40.0})

    def test_corpo_invalido_devolve_none(self):
        for lixo in (None, "", "isto não é json", "[1, 2]", '{"caudal": 1}'):
            self.assertIsNone(mensagens.interpretar_corpo(lixo), lixo)


class TestLer(unittest.TestCase):

    def test_separa_os_campos(self):
        corpo = json.dumps({"tipo": "proposta_descarga", "caudal": 40.0})
        r = mensagens.ler(falsa(corpo))
        self.assertEqual((r.remetente, r.performativa, r.protocolo, r.thread, r.tipo),
                         ("barragem", "propose", "negociar-descarga",
                          "desc-001", "proposta_descarga"))
        self.assertEqual(r.corpo["caudal"], 40.0)

    def test_timeout_devolve_none(self):
        self.assertIsNone(mensagens.ler(None))

    def test_corpo_invalido_nao_rebenta(self):
        self.assertIsNone(mensagens.ler(falsa("lixo")))


class TestNovoId(unittest.TestCase):

    def test_ids_sucessivos_por_prefixo(self):
        self.assertEqual(mensagens.novo_id("teste-a"), "teste-a-001")
        self.assertEqual(mensagens.novo_id("teste-a"), "teste-a-002")
        self.assertEqual(mensagens.novo_id("teste-b"), "teste-b-001")


class TestValidacao(unittest.TestCase):

    def test_performativa_ou_protocolo_desconhecidos(self):
        with self.assertRaises(ValueError):
            mensagens.criar("liderA", "grito", "votacao", "voto")
        with self.assertRaises(ValueError):
            mensagens.criar("liderA", "inform", "inventado", "voto")
        with self.assertRaises(ValueError):
            mensagens.template("inventado")


@unittest.skipUnless(TEM_SPADE, "SPADE não está disponível")
class TestComSpade(unittest.TestCase):

    def test_criar_e_template_encaixam(self):
        msg = mensagens.criar("liderA", "propose", "negociar-descarga",
                              "proposta_descarga", thread="desc-007", caudal=40.0)
        self.assertEqual(msg.thread, "desc-007")
        self.assertTrue(mensagens.template("negociar-descarga", "propose").match(msg))
        self.assertTrue(mensagens.template("negociar-descarga").match(msg))
        self.assertFalse(mensagens.template("votacao", "propose",
                                            "inform").match(msg))
        self.assertTrue(mensagens.template("negociar-descarga", "inform",
                                           "propose").match(msg))
        self.assertFalse(mensagens.template("negociar-descarga",
                                            thread="desc-999").match(msg))

    def test_um_voto_nao_se_confunde_com_outra_mensagem(self):
        voto = mensagens.criar("barragem", "accept-proposal", "votacao", "voto")
        outra = mensagens.criar("barragem", "inform", "alerta-risco", "alerta")
        t = mensagens.template("votacao", "accept-proposal", "reject-proposal")
        self.assertTrue(t.match(voto))
        self.assertFalse(t.match(outra))


if __name__ == "__main__":
    unittest.main()
