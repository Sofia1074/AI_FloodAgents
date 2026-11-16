"""Experimentos: corre cenários mudando um parâmetro de cada vez (tarefa t27).

Cada experimento é uma execução normal de `main.py <cenário>`, num processo à
parte, com duas variáveis de ambiente:

- FLOOD_PARAMETROS (JSON) muda constantes do config.py, por exemplo
  {"MAX_RODADAS": 1} (ver o fim do config.py);
- FLOOD_SAIDA guarda as métricas em resultados/experimentos/, para não
  sobrescrever os resultados que vão para os slides.

No fim junta o resumo de cada execução numa tabela:
resultados/experimentos/comparacao.csv. A tabela acumula: voltar a correr um
experimento substitui a sua linha.

Correr com um Python que tenha o SPADE (cada execução demora cerca de 1,5
minutos):

    python experimentos.py --lista          mostra o plano, sem correr nada
    python experimentos.py                  corre todos os grupos
    python experimentos.py base rodadas     corre só estes grupos

Os grupos mudam um parâmetro de cada vez e comparam-se com a linha "base"
do mesmo cenário (corra primeiro o grupo "base").
"""

import csv
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(RAIZ, "resultados", "experimentos")
TABELA = os.path.join(PASTA, "comparacao.csv")

CAMPOS = ["experimento", "cenario", "mensagens", "alertas", "deteccao_media_s",
          "votacoes_aprovadas", "votacoes_rejeitadas", "descargas",
          "recursos_usados", "transacoes", "nivel_max_A", "nivel_max_B",
          "nivel_max_C", "ciclos_em_risco_elevado"]

# a mitigação deixa de ter efeito físico: as bombas, as barreiras e as equipas
# duram um ciclo e não escoam nem protegem nada
SEM_EFEITO = {recurso: {"drenagem": 0.0, "protecao": 0.0, "ciclos": 1}
              for recurso in ("bombas", "equipas", "barreiras", "sacos_areia")}

# grupo -> [(nome do experimento, cenário, parâmetros do config.py)]
GRUPOS = {
    "base": [("base", c, {}) for c in ("risco_elevado", "conflito", "recursos_limitados")],
    "rodadas": [("1 rodada", "conflito", {"MAX_RODADAS": 1})],
    "mitigacao": [("sem efeito", c, {"EFEITO_RECURSO": SEM_EFEITO})
                  for c in ("risco_elevado", "conflito")],
    "subida_rapida": [("limiar 3", "risco_elevado", {"LIMIAR_SUBIDA_RAPIDA": 3.0}),
                      ("limiar 6", "risco_elevado", {"LIMIAR_SUBIDA_RAPIDA": 6.0})],
    "medicao": [("medir a cada 5 s", c, {"PERIODO_MEDICAO": 5})
                for c in ("risco_elevado", "conflito")],
}


def pasta_do(nome, cenario):
    """Pasta onde um experimento guarda as suas métricas."""
    seguro = "".join(c if c.isalnum() else "_" for c in nome)
    return os.path.join(PASTA, seguro, cenario)


def correr(nome, cenario, parametros, tempo_maximo=300):
    """Corre `main.py <cenário>` com os parâmetros dados.

    Args:
        nome (str): Nome do experimento, como "1 rodada".
        cenario (str): Uma chave de `CENARIOS`.
        parametros (dict): Constantes do config.py a mudar.
        tempo_maximo (int): Segundos antes de desistir da execução.

    Returns:
        dict: O `resumo.json` que a execução gravou.

    Raises:
        RuntimeError: Se a execução falhar ou não gravar o resumo.
    """
    saida = pasta_do(nome, cenario)
    ambiente = dict(os.environ, FLOOD_PARAMETROS=json.dumps(parametros),
                    FLOOD_SAIDA=saida, PYTHONIOENCODING="utf-8")
    processo = subprocess.run([sys.executable, "main.py", cenario], cwd=RAIZ,
                              env=ambiente, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=tempo_maximo)
    ficheiro = os.path.join(saida, "resumo.json")
    if processo.returncode != 0 or not os.path.isfile(ficheiro):
        fim = "\n".join(processo.stderr.strip().splitlines()[-5:])
        raise RuntimeError(f"{nome} em {cenario} falhou (código "
                           f"{processo.returncode}):\n{fim}")
    with open(ficheiro, encoding="utf-8") as f:
        return json.load(f)


def linha(nome, resumo):
    """Uma linha da tabela, a partir do resumo de uma execução.

    Args:
        nome (str): Nome do experimento.
        resumo (dict): O `resumo.json` da execução.

    Returns:
        dict: Os valores de `CAMPOS`.
    """
    deteccoes = [v for v in resumo["tempo_deteccao_s"].values() if v is not None]
    propostas = resumo["propostas"]
    return {
        "experimento": nome,
        "cenario": resumo["cenario"],
        "mensagens": resumo["mensagens"]["total"],
        "alertas": resumo["alertas"],
        "deteccao_media_s": (round(sum(deteccoes) / len(deteccoes), 1)
                             if deteccoes else ""),
        "votacoes_aprovadas": propostas["aprovadas"],
        "votacoes_rejeitadas": propostas["rejeitadas_votacao"],
        "descargas": propostas["descargas"],
        "recursos_usados": sum(resumo["recursos"]["total"].values()),
        "transacoes": resumo["transacoes"]["total"],
        "nivel_max_A": round(resumo["nivel_maximo"]["A"], 1),
        "nivel_max_B": round(resumo["nivel_maximo"]["B"], 1),
        "nivel_max_C": round(resumo["nivel_maximo"]["C"], 1),
        "ciclos_em_risco_elevado": sum(resumo["ciclos_em_risco_elevado"].values()),
    }


def juntar(existentes, nova):
    """Acrescenta uma linha à tabela, substituindo a do mesmo experimento e cenário.

    Args:
        existentes (list): Linhas já na tabela.
        nova (dict): A linha a acrescentar.

    Returns:
        list: As linhas, por cenário, com "base" primeiro em cada cenário.
    """
    chave = (nova["experimento"], nova["cenario"])
    linhas = [l for l in existentes if (l["experimento"], l["cenario"]) != chave]
    linhas.append(nova)
    return sorted(linhas, key=lambda l: (l["cenario"], l["experimento"] != "base",
                                         l["experimento"]))


def ler_tabela():
    """Lê a tabela gravada, ou uma lista vazia se ainda não existe."""
    if not os.path.isfile(TABELA):
        return []
    with open(TABELA, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def gravar_tabela(linhas):
    """Escreve a tabela em resultados/experimentos/comparacao.csv."""
    os.makedirs(PASTA, exist_ok=True)
    with open(TABELA, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(linhas)


def mostrar(linhas):
    """Escreve a tabela no terminal, alinhada."""
    cabecalho = ["experimento", "cenario", "msgs", "alertas", "deteção s", "votos ok",
                 "votos não", "descargas", "recursos", "transações", "A", "B", "C",
                 "ciclos risco"]
    tabela = [cabecalho] + [[str(l[c]) for c in CAMPOS] for l in linhas]
    larguras = [max(len(linha_[i]) for linha_ in tabela) for i in range(len(cabecalho))]
    for linha_ in tabela:
        print("  ".join(v.ljust(w) for v, w in zip(linha_, larguras)))


def main(argv):
    """Escolhe os grupos, corre-os e grava a tabela depois de cada execução."""
    grupos = [a for a in argv if not a.startswith("-")] or list(GRUPOS)
    desconhecidos = [g for g in grupos if g not in GRUPOS]
    if desconhecidos:
        sys.exit(f"Grupo desconhecido: {', '.join(desconhecidos)}. "
                 f"Opções: {', '.join(GRUPOS)}")
    plano = [(nome, cenario, params) for g in grupos for nome, cenario, params in GRUPOS[g]]

    if "--lista" in argv:
        for nome, cenario, params in plano:
            alteracao = "(sem alterações)" if not params else ", ".join(params)
            print(f"{cenario:20s} {nome:18s} {alteracao}")
        print(f"{len(plano)} execuções, cerca de {len(plano) * 1.5:.0f} minutos")
        return

    linhas = ler_tabela()
    for i, (nome, cenario, params) in enumerate(plano, 1):
        print(f"[{i}/{len(plano)}] {nome} em {cenario}...", flush=True)
        try:
            linhas = juntar(linhas, linha(nome, correr(nome, cenario, params)))
        except (RuntimeError, subprocess.TimeoutExpired) as erro:
            print(f"  falhou: {erro}", flush=True)
            continue
        gravar_tabela(linhas)           # guarda já, para não perder o que correu
    print()
    mostrar(linhas)
    print(f"\nTabela em {os.path.relpath(TABELA, RAIZ)}")


if __name__ == "__main__":
    main(sys.argv[1:])
