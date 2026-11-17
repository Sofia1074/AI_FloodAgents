"""Gera a documentação HTML do código, a partir dos docstrings (formato Google).

Correr, na pasta do projeto e com o ambiente ativo:

    python gerar_docs.py

Escreve em `docs/html/` (abrir `docs/html/index.html`). Usa o pdoc, que importa
os módulos: por isso precisa do SPADE, do spade_bdi e do matplotlib instalados
(`pip install -r requirements.txt`).

Os módulos dos agentes têm de ser nomeados um a um: o `agentes/__init__.py`
define `__all__`, e o pdoc só mostra então as classes lá listadas e esconde o
resto de cada módulo (funções soltas como `reformular` ou
`executar_contingencia`).
"""

import subprocess
import sys

MODULOS = [
    "main", "config", "ambiente", "risco", "cenarios", "mensagens", "rede",
    "mercado", "metricas", "graficos", "experimentos", "registo",
    "agentes", "agentes.barragem", "agentes.operador", "agentes.lider",
    "agentes.diretorio", "agentes.contract_net",
]
PASTA_SAIDA = "docs/html"


def main():
    """Corre o pdoc sobre `MODULOS` e escreve o HTML em `PASTA_SAIDA`.

    Returns:
        int: O código de saída do pdoc (0 se correu bem).
    """
    comando = [sys.executable, "-m", "pdoc", "--docformat", "google",
               "-o", PASTA_SAIDA, *MODULOS]
    resultado = subprocess.run(comando)
    if resultado.returncode == 0:
        print(f"Documentação gerada em {PASTA_SAIDA}/index.html")
    return resultado.returncode


if __name__ == "__main__":
    sys.exit(main())
