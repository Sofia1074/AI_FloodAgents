"""Ponto de entrada: cria o ambiente e os agentes, e corre a simulação.

Correr com um Python que tenha o SPADE instalado:
         python main.py                       (cenário por omissão, saída resumida)
         python main.py conflito              (escolhe o cenário)
         python main.py recursos_limitados -v (mostra também cada mensagem
                                               e cada ciclo do ambiente)

Cenários: risco_elevado, conflito, recursos_limitados (os três do guia),
calmo e cheia (testes).

No fim grava as métricas em resultados/<cenário>/ (ciclos.csv, eventos.csv,
resumo.json). Os gráficos fazem-se depois com graficos.py.
"""

import asyncio
import os
import sys

import spade

import metricas
import registo
from agentes import CommunityLeader, DamOperator, NeighbourhoodOperator
from ambiente import Ambiente
from cenarios import CENARIO_POR_OMISSAO, CENARIOS
from config import PERIODO_CICLO

DURACAO = 60   # segundos de simulação


def estado(barragem, operadores):
    bairros = "  ".join(f"{op.bairro}: {op.nivel_agua:.1f} ({op.avaliar_risco()})"
                        for op in operadores)
    return f"reservatório {barragem.nivel_reservatorio:.1f}% | {bairros}"


async def simular(ambiente):
    """Avança o ambiente um passo a cada PERIODO_CICLO segundos.
    Mostra um evento quando a chuva muda e cada ciclo em modo verboso."""
    chuva_anterior = None
    while True:
        await asyncio.sleep(PERIODO_CICLO)
        chuva = ambiente.chuva_atual()
        if chuva != chuva_anterior:
            registo.evento("CHUVA", f"{chuva:.0f} mm por ciclo" if chuva else "parou")
            chuva_anterior = chuva
        ambiente.passo()
        metricas.registar_ciclo()
        registo.detalhe("ambiente", ambiente.resumo())


def mostrar_metricas(r):
    """Escreve no terminal as métricas principais, em poucas linhas."""
    det = " ".join(f"{b}:{'-' if c is None else f'{c} ciclos'}"
                   for b, c in r["tempo_deteccao_ciclos"].items())
    p = r["propostas"]
    tempos = r["tempo_ate_decisao_s"]
    decisao = f"{1000 * sum(tempos) / len(tempos):.0f} ms" if tempos else "-"
    print(f"Métricas: mensagens {r['mensagens']['total']} | deteção {det} | "
          f"decisão média {decisao}", flush=True)
    print(f"          propostas {p['total']} (aprovadas {p['aprovadas']}, rejeitadas "
          f"na votação {p['rejeitadas_votacao']}, por segurança "
          f"{p['rejeitadas_seguranca']}) | recursos {r['recursos']['total'] or '-'} | "
          f"transações {r['transacoes']['total']}", flush=True)


async def main(nome_cenario, verboso):
    registo.iniciar(verboso)
    ambiente = Ambiente(CENARIOS[nome_cenario])
    recolha = metricas.iniciar(nome_cenario, ambiente)
    metricas.registar_ciclo()            # estado inicial (ciclo 0)
    metricas.instalar_contador_mensagens()
    barragem = DamOperator("barragem", ambiente)
    operadores = [NeighbourhoodOperator(f"op{b}", b, ambiente) for b in "ABC"]
    lideres = [CommunityLeader(f"lider{b}", b) for b in "ABC"]

    print(f"=== Cenário '{nome_cenario}' | {DURACAO}s | "
          f"{'verboso' if verboso else 'resumido (use -v para ver as mensagens)'} ===",
          flush=True)
    print(f"Estado inicial: {estado(barragem, operadores)}", flush=True)

    todos = [*lideres, *operadores, barragem]
    for agente in todos:
        await agente.start(auto_register=True)
    registo.detalhe("main", "7 agentes ativos")
    # os operadores só medem quando todos estão ativos: assim o primeiro
    # alerta nunca chega a um líder que ainda não está ligado
    for operador in operadores:
        operador.comecar()

    relogio = asyncio.create_task(simular(ambiente))
    await asyncio.sleep(DURACAO)
    relogio.cancel()

    for agente in todos:
        await agente.stop()

    print("=== Fim ===", flush=True)
    print(f"Estado final: {estado(barragem, operadores)}", flush=True)
    print(f"Ciclos do ambiente: {ambiente.ciclo} | descargas executadas: "
          f"{barragem.descargas} (contingências: {barragem.contingencias}) | "
          f"planos rejeitados: {barragem.rejeitados}", flush=True)
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "resultados", nome_cenario)
    recolha.exportar(pasta)
    mostrar_metricas(recolha.resumo())
    print(f"Métricas gravadas em resultados/{nome_cenario}/", flush=True)


def ler_argumentos(argv):
    """Devolve (cenário, verboso) a partir da linha de comando."""
    verboso = "-v" in argv or "--verbose" in argv
    nomes = [a for a in argv[1:] if not a.startswith("-")]
    nome = nomes[0] if nomes else CENARIO_POR_OMISSAO
    if nome not in CENARIOS:
        sys.exit(f"Cenário desconhecido: {nome}. Opções: {', '.join(CENARIOS)}")
    return nome, verboso


if __name__ == "__main__":
    spade.run(main(*ler_argumentos(sys.argv)), embedded_xmpp_server=True)
