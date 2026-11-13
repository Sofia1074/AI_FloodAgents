"""Gráficos dos resultados, para os slides (tarefa t17).

Lê o que main.py gravou em resultados/<cenário>/ e desenha, para cada cenário:

    nivel_bairros.png   chuva por ciclo (em cima) e nível da água de cada bairro
                        com as faixas de risco (em baixo); descargas sombreadas
    reservatorio.png    nível do reservatório com o limiar de alerta (em cima)
                        e caudal de descarga (em baixo)

e uma tabela com as métricas dos cenários lado a lado:

    resultados/resumo_cenarios.csv

Precisa de matplotlib (não precisa de SPADE). Correr depois das simulações:
    python graficos.py
"""

import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from config import LIMITES_RISCO, NIVEL_ALERTA_RESERVATORIO, PERIODO_CICLO  # noqa: E402

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")

# Paleta: três primeiros tons categóricos da paleta de referência
# (validados todos contra todos, incluindo daltonismo). O verde-água fica
# abaixo de 3:1 de contraste, por isso cada linha leva rótulo direto.
COR_BAIRRO = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}
NOME_BAIRRO = {"A": "A (junto ao rio)", "B": "B (centro)", "C": "C (zona alta)"}
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_FRACA = "#898781"
GRELHA = "#e1e0d9"
EIXO = "#c3c2b7"
DESCARGA = "#e9eef5"
CHUVA = "#86b6ef"

TITULOS = {
    "risco_elevado": "Cenário 1: risco elevado num bairro",
    "conflito": "Cenário 2: conflito de interesses na descarga",
    "recursos_limitados": "Cenário 3: recursos limitados",
    "calmo": "Teste: calmo",
    "cheia": "Teste: cheia",
}

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
    "font.size": 11,
    "axes.edgecolor": EIXO,
    "axes.labelcolor": TINTA_2,
    "axes.titlecolor": TINTA,
    "xtick.color": TINTA_FRACA,
    "ytick.color": TINTA_FRACA,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "savefig.facecolor": SUPERFICIE,
})


def ler_ciclos(pasta):
    """Lê ciclos.csv e devolve uma lista de dicts com números convertidos."""
    with open(os.path.join(pasta, "ciclos.csv"), encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        for k, v in linha.items():
            if not k.startswith("risco_"):
                linha[k] = float(v)
    return linhas


def ler_descargas(pasta):
    """Devolve [(ciclo_inicio, ciclo_fim)] das descargas, a partir de eventos.csv."""
    periodos = []
    with open(os.path.join(pasta, "eventos.csv"), encoding="utf-8") as f:
        for e in csv.DictReader(f):
            if e["tipo"] == "descarga":
                inicio = int(e["ciclo"])
                duracao = json.loads(e["detalhe"]).get("duracao", 0)
                periodos.append((inicio, inicio + duracao))
    return periodos


def _grelha(ax):
    ax.grid(axis="y", color=GRELHA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _afastar(posicoes, distancia):
    """Afasta verticalmente rótulos que ficariam uns em cima dos outros.

    Args:
        posicoes: {rótulo: y} na ordem que se quiser.
        distancia: espaço mínimo entre dois rótulos, nas unidades do eixo.
    Returns:
        {rótulo: y ajustado}.
    """
    ordem = sorted(posicoes.items(), key=lambda par: par[1])
    ajustadas = {}
    anterior = None
    for nome, y in ordem:
        if anterior is not None and y - anterior < distancia:
            y = anterior + distancia
        ajustadas[nome] = y
        anterior = y
    return ajustadas


def _juntar(periodos, fim_dados):
    """Corta os períodos no fim dos dados e junta os que se tocam."""
    blocos = []
    for ini, fim in sorted(periodos):
        fim = min(fim, fim_dados)
        if ini >= fim_dados:
            continue
        if blocos and ini <= blocos[-1][1]:
            blocos[-1] = (blocos[-1][0], max(blocos[-1][1], fim), blocos[-1][2] + 1)
        else:
            blocos.append((ini, fim, 1))
    return blocos


def _sombrear_descargas(ax, descargas, fim_dados, rotulo=True):
    """Sombreia os períodos de descarga e marca o início de cada uma."""
    for ini, fim, n in _juntar(descargas, fim_dados):
        ax.axvspan(ini, fim, color=DESCARGA, zorder=0, linewidth=0)
        if rotulo:
            texto = "descarga" if n == 1 else f"{n} descargas seguidas"
            ax.text((ini + fim) / 2, 0.98, texto, transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=9, color=TINTA_2)
    if rotulo and len(descargas) > 1:
        for i, (ini, _) in enumerate(sorted(descargas), start=1):
            if ini < fim_dados:
                ax.axvline(ini, color=EIXO, linewidth=0.8, zorder=1)
                ax.text(ini + 0.15, 0.91, str(i), transform=ax.get_xaxis_transform(),
                        ha="left", va="top", fontsize=8, color=TINTA_FRACA)


def grafico_bairros(cenario, ciclos, descargas, destino):
    """Chuva por ciclo e nível da água de cada bairro, com faixas de risco."""
    x = [l["ciclo"] for l in ciclos]
    fig, (ax_chuva, ax) = plt.subplots(
        2, 1, figsize=(11, 6.2), sharex=True,
        gridspec_kw={"height_ratios": [1, 3.2], "hspace": 0.08})

    # chuva
    ax_chuva.bar(x, [l["chuva"] for l in ciclos], width=0.7, color=CHUVA, linewidth=0)
    ax_chuva.set_ylabel("chuva\n(mm/ciclo)", fontsize=10)
    _grelha(ax_chuva)
    _sombrear_descargas(ax_chuva, descargas, x[-1], rotulo=False)

    # faixas de risco: linhas finas nos limites e o nome de cada faixa à direita
    limites = [0.0] + [lim for lim, _ in LIMITES_RISCO] + [100.0]
    nomes = [nome for _, nome in LIMITES_RISCO] + ["crítico"]
    for lim in limites[1:-1]:
        ax.axhline(lim, color=EIXO, linewidth=0.9, zorder=1)
    for (baixo, alto), nome in zip(zip(limites, limites[1:]), nomes):
        ax.text(1.005, (baixo + alto) / 2, nome, transform=ax.get_yaxis_transform(),
                va="center", ha="left", fontsize=9, color=TINTA_FRACA)
    _sombrear_descargas(ax, descargas, x[-1])

    finais = {}
    for b, cor in COR_BAIRRO.items():
        y = [l[f"nivel_{b}"] for l in ciclos]
        ax.plot(x, y, color=cor, linewidth=2, label=NOME_BAIRRO[b], zorder=3,
                solid_capstyle="round")
        finais[b] = y[-1]
    for b, y in _afastar(finais, distancia=4.5).items():
        ax.text(x[-1] + 0.4, y, b, color=TINTA, fontsize=10, fontweight="bold",
                va="center", ha="left")

    ax.set_ylim(0, 100)
    ax.set_xlim(x[0], x[-1] + 1.5)
    ax.set_ylabel("nível da água (% da capacidade)")
    ax.set_xlabel(f"ciclo do ambiente (1 ciclo = {PERIODO_CICLO} s)")
    _grelha(ax)
    ax.grid(False)          # as linhas dos limites de risco fazem de grelha
    fig.suptitle(TITULOS.get(cenario, cenario), x=0.06, ha="left", fontsize=14,
                 color=TINTA, fontweight="semibold")
    fig.legend(*ax.get_legend_handles_labels(), loc="upper right", frameon=False,
               ncol=3, fontsize=10, bbox_to_anchor=(0.98, 0.99), labelcolor=TINTA_2)
    fig.savefig(destino, dpi=200, bbox_inches="tight")
    plt.close(fig)


def grafico_reservatorio(cenario, ciclos, descargas, destino):
    """Nível do reservatório (com o limiar de alerta) e caudal de descarga."""
    x = [l["ciclo"] for l in ciclos]
    fig, (ax, ax_caudal) = plt.subplots(
        2, 1, figsize=(11, 5.2), sharex=True,
        gridspec_kw={"height_ratios": [2.4, 1], "hspace": 0.1})

    _sombrear_descargas(ax, descargas, x[-1])
    ax.axhline(NIVEL_ALERTA_RESERVATORIO, color=TINTA_FRACA, linewidth=1, zorder=1)
    ax.text(x[0] + 0.3, NIVEL_ALERTA_RESERVATORIO + 0.6,
            f"nível de alerta ({NIVEL_ALERTA_RESERVATORIO:.0f}%)",
            fontsize=9, color=TINTA_2, va="bottom")
    nivel = [l["reservatorio"] for l in ciclos]
    ax.plot(x, nivel, color=COR_BAIRRO["A"], linewidth=2, zorder=3)
    ax.set_ylabel("reservatório (%)")
    baixo = min(min(nivel), NIVEL_ALERTA_RESERVATORIO) - 5
    ax.set_ylim(max(0, baixo), min(100, max(max(nivel), NIVEL_ALERTA_RESERVATORIO) + 5))
    _grelha(ax)

    _sombrear_descargas(ax_caudal, descargas, x[-1], rotulo=False)
    ax_caudal.set_xlim(x[0] - 0.5, x[-1] + 0.5)
    ax_caudal.bar(x, [l["caudal_saida"] for l in ciclos], width=0.7,
                  color=COR_BAIRRO["A"], linewidth=0)
    ax_caudal.set_ylabel("caudal de\ndescarga", fontsize=10)
    ax_caudal.set_xlabel(f"ciclo do ambiente (1 ciclo = {PERIODO_CICLO} s)")
    _grelha(ax_caudal)

    fig.suptitle(f"{TITULOS.get(cenario, cenario)}: barragem", x=0.06, ha="left",
                 fontsize=14, color=TINTA, fontweight="semibold")
    fig.savefig(destino, dpi=200, bbox_inches="tight")
    plt.close(fig)


def tabela_resumo(cenarios, destino):
    """Escreve as métricas principais dos cenários lado a lado (CSV)."""
    linhas = []
    for c in cenarios:
        with open(os.path.join(PASTA, c, "resumo.json"), encoding="utf-8") as f:
            r = json.load(f)
        tempos = r["tempo_ate_decisao_s"]
        det = [v for v in r["tempo_deteccao_s"].values() if v is not None]
        linhas.append({
            "cenario": c,
            "mensagens": r["mensagens"]["total"],
            "alertas": r["alertas"],
            "deteccao_media_s": round(sum(det) / len(det), 1) if det else "",
            "propostas": r["propostas"]["total"],
            "aprovadas": r["propostas"]["aprovadas"],
            "rejeitadas_votacao": r["propostas"]["rejeitadas_votacao"],
            "rejeitadas_seguranca": r["propostas"]["rejeitadas_seguranca"],
            "decisao_media_ms": round(1000 * sum(tempos) / len(tempos)) if tempos else "",
            "recursos_usados": sum(r["recursos"]["total"].values()),
            "transacoes": r["transacoes"]["total"],
            "nivel_max_A": r["nivel_maximo"]["A"],
            "nivel_max_B": r["nivel_maximo"]["B"],
            "nivel_max_C": r["nivel_maximo"]["C"],
        })
    with open(destino, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)


def main():
    if not os.path.isdir(PASTA):
        raise SystemExit("Não há resultados/. Corra primeiro: python main.py <cenário>")
    feitos = []
    for cenario in sorted(os.listdir(PASTA)):
        pasta = os.path.join(PASTA, cenario)
        if not os.path.isfile(os.path.join(pasta, "ciclos.csv")):
            continue
        ciclos = ler_ciclos(pasta)
        descargas = ler_descargas(pasta)
        grafico_bairros(cenario, ciclos, descargas, os.path.join(pasta, "nivel_bairros.png"))
        grafico_reservatorio(cenario, ciclos, descargas,
                             os.path.join(pasta, "reservatorio.png"))
        feitos.append(cenario)
        print(f"{cenario}: nivel_bairros.png, reservatorio.png")
    if feitos:
        tabela_resumo(feitos, os.path.join(PASTA, "resumo_cenarios.csv"))
        print("resumo_cenarios.csv")


if __name__ == "__main__":
    main()
