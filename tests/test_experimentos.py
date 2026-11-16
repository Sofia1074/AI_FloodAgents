"""Testes dos experimentos (sem SPADE): o gancho do config.py e a tabela.

Correr:  python -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import experimentos  # noqa: E402

RESUMO = {
    "cenario": "conflito",
    "mensagens": {"total": 50},
    "alertas": 13,
    "tempo_deteccao_s": {"A": 0, "B": 4, "C": None},
    "propostas": {"aprovadas": 1, "rejeitadas_votacao": 0, "descargas": 1},
    "recursos": {"total": {"bombas": 5, "barreiras": 2}},
    "transacoes": {"total": 1},
    "nivel_maximo": {"A": 62.76, "B": 37.18, "C": 35.0},
    "ciclos_em_risco_elevado": {"A": 8, "B": 0, "C": 2},
}


def valor_do_config(parametros):
    """Valor de MAX_RODADAS e do LIMIAR_SUBIDA_RAPIDA num processo novo."""
    ambiente = dict(os.environ, FLOOD_PARAMETROS=json.dumps(parametros))
    saida = subprocess.run(
        [sys.executable, "-c",
         "import config; print(config.MAX_RODADAS, config.LIMIAR_SUBIDA_RAPIDA)"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True, check=True).stdout
    return saida.split()


class TestGanchoDoConfig(unittest.TestCase):

    def test_sem_parametros_fica_tudo_como_esta(self):
        import config
        self.assertEqual(valor_do_config({}),
                         [str(config.MAX_RODADAS), str(config.LIMIAR_SUBIDA_RAPIDA)])

    def test_muda_so_o_que_foi_pedido(self):
        import config
        self.assertEqual(valor_do_config({"MAX_RODADAS": 1}),
                         ["1", str(config.LIMIAR_SUBIDA_RAPIDA)])


class TestTabela(unittest.TestCase):

    def test_linha_resume_o_resumo(self):
        linha = experimentos.linha("base", RESUMO)
        self.assertEqual(linha["mensagens"], 50)
        self.assertEqual(linha["deteccao_media_s"], 2.0)       # ignora o None
        self.assertEqual(linha["recursos_usados"], 7)
        self.assertEqual(linha["ciclos_em_risco_elevado"], 10)
        self.assertEqual(set(linha), set(experimentos.CAMPOS))

    def test_linha_sem_deteccao_fica_vazia(self):
        resumo = dict(RESUMO, tempo_deteccao_s={"A": None, "B": None, "C": None})
        self.assertEqual(experimentos.linha("base", resumo)["deteccao_media_s"], "")

    def test_juntar_substitui_a_linha_repetida_e_poe_a_base_primeiro(self):
        base = experimentos.linha("base", RESUMO)
        outra = experimentos.linha("1 rodada", RESUMO)
        tabela = experimentos.juntar(experimentos.juntar([], outra), base)
        self.assertEqual([l["experimento"] for l in tabela], ["base", "1 rodada"])
        nova = dict(base, mensagens=99)
        tabela = experimentos.juntar(tabela, nova)
        self.assertEqual(len(tabela), 2)
        self.assertEqual(tabela[0]["mensagens"], 99)

    def test_todos_os_grupos_usam_cenarios_que_existem(self):
        from cenarios import CENARIOS
        for grupo, execucoes in experimentos.GRUPOS.items():
            for nome, cenario, _ in execucoes:
                self.assertIn(cenario, CENARIOS, f"{grupo}/{nome}")


if __name__ == "__main__":
    unittest.main()
