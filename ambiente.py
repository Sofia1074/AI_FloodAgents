"""Ambiente simulado: barragem, rio a jusante e os três bairros.

O ambiente não é um agente. É o "mundo" que os agentes observam e alteram:
os operadores leem o nível de água do seu bairro, a barragem define o caudal
de descarga e a mitigação (bombas, barreiras, equipas) muda a forma como a
água entra e sai de cada bairro.

O estado inicial vem de um cenário (cenarios.py). A cada ciclo, `passo()`
aplica as regras abaixo, por esta ordem:

1. A chuva do ciclo define o caudal de entrada no reservatório.
2. O reservatório sobe com a entrada e desce com a descarga em curso.
3. O nível a jusante acompanha o caudal de descarga.
4. Em cada bairro a água sobe com a chuva (mais com o solo encharcado) e com
   a parte da descarga que lhe chega, e desce com a drenagem.
5. A humidade do solo sobe com a chuva e desce devagar sem ela.
6. Os efeitos temporários dos recursos de mitigação perdem um ciclo.

Limitações (o guia pede que fiquem documentadas):

- Não é um modelo hidrológico. As relações são lineares e os números de
  config.py foram escolhidos para os cenários terem um comportamento
  plausível, não para prever inundações.
- A descarga chega a todos os bairros no mesmo ciclo, sem tempo de
  propagação no rio.
- O nível do bairro está em percentagem da capacidade de retenção (0 a 100);
  o nível a jusante está em metros, mas só serve de indicador.
- As medições não têm ruído nem falhas de sensor.
"""

from dataclasses import dataclass, field

from config import (AREA_BACIA, CAPACIDADE_RESERVATORIO, CAPACIDADE_TANQUE,
                    CAUDAL_BASE_ENTRADA, EFEITO_RECURSO, FATOR_JUSANTE,
                    HUMIDADE_POR_MM, NIVEL_JUSANTE_BASE, PERDA_DRENAGEM_SOLO,
                    PROTECAO_MAXIMA, SECAGEM_SOLO)


def _limitar(valor, minimo, maximo):
    """Devolve `valor` preso ao intervalo [minimo, maximo]."""
    return max(minimo, min(maximo, valor))


@dataclass
class Bairro:
    """Estado físico de um bairro.

    Attributes:
        nome: "A", "B" ou "C".
        nivel: água acumulada, em % da capacidade de retenção (0 a 100).
        humidade: humidade do solo, de 0 (seco) a 1 (encharcado).
        drenagem_base: água escoada por ciclo com o solo seco.
        fator_chuva: quanto da chuva vira água acumulada (ruas impermeáveis > 1).
        exposicao: fração do caudal de descarga que chega ao bairro.
        velocidade: variação do nível no último ciclo (positiva = a subir).
        estoque: recursos físicos guardados no bairro (bombas, barreiras...).
        moeda: saldo fictício do bairro, gerido pelo líder.
        populacao: habitantes, usado pelos líderes para definir prioridades.
        efeitos: recursos de mitigação ativos, cada um com os ciclos que faltam.
    """

    nome: str
    nivel: float = 0.0
    humidade: float = 0.0
    drenagem_base: float = 2.0
    fator_chuva: float = 0.5
    exposicao: float = 0.05
    velocidade: float = 0.0
    estoque: dict = field(default_factory=dict)
    moeda: float = 0.0
    populacao: int = 0
    efeitos: list = field(default_factory=list)

    def entrada_chuva(self, chuva):
        """Água que `chuva` mm acrescentam ao bairro num ciclo
        (mais com o solo encharcado)."""
        return chuva * self.fator_chuva * (1.0 + self.humidade)

    def drenagem_natural(self):
        """Água escoada por ciclo pelo próprio bairro, sem bombas nem
        equipas: menor com o solo encharcado."""
        return self.drenagem_base * (1.0 - PERDA_DRENAGEM_SOLO * self.humidade)

    def drenagem(self):
        """Água escoada por ciclo, somando bombas e equipas ativas."""
        return self.drenagem_natural() + sum(e["drenagem"] for e in self.efeitos)

    def protecao(self):
        """Fração da água da descarga travada pelas barreiras ativas."""
        return min(PROTECAO_MAXIMA, sum(e["protecao"] for e in self.efeitos))


class Ambiente:
    """O mundo simulado, partilhado por todos os agentes.

    Args:
        cenario: dicionário de cenarios.py com "reservatorio", "chuva"
            (mm por ciclo; depois do fim da lista não chove) e "bairros".
    """

    def __init__(self, cenario):
        self.ciclo = 0
        self.nivel_reservatorio = float(cenario["reservatorio"])
        self.chuva = list(cenario.get("chuva", []))
        self.chuva_ultimo_ciclo = 0.0    # chuva do ciclo que acabou de passar
        self.caudal_entrada = CAUDAL_BASE_ENTRADA
        self.caudal_saida = 0.0
        self.nivel_jusante = NIVEL_JUSANTE_BASE
        self._descarga = {"caudal": 0.0, "atraso": 0, "ciclos": 0}
        self.bairros = {}
        for nome, dados in cenario["bairros"].items():
            self.bairros[nome] = Bairro(
                nome=nome,
                nivel=float(dados.get("nivel", 0.0)),
                humidade=float(dados.get("humidade", 0.0)),
                drenagem_base=float(dados.get("drenagem", 2.0)),
                fator_chuva=float(dados.get("fator_chuva", 0.5)),
                exposicao=float(dados.get("exposicao", 0.05)),
                estoque=dict(dados.get("estoque", {})),
                moeda=float(dados.get("moeda", 0.0)),
                populacao=int(dados.get("populacao", 0)),
            )

    # ---- leitura ------------------------------------------------------

    def chuva_atual(self):
        """Chuva prevista para o ciclo atual, em mm."""
        return self.chuva[self.ciclo] if self.ciclo < len(self.chuva) else 0.0

    def descarga_ativa(self):
        """True enquanto houver uma descarga marcada ou a decorrer."""
        return self._descarga["ciclos"] > 0

    def resumo(self):
        """Texto curto com o estado atual, para o registo do terminal."""
        bairros = " ".join(f"{b.nome}:{b.nivel:.0f}({b.velocidade:+.1f})"
                           for b in self.bairros.values())
        return (f"ciclo {self.ciclo} chuva {self.chuva_atual():.0f} | "
                f"reservatório {self.nivel_reservatorio:.1f}% saída "
                f"{self.caudal_saida:.0f} | jusante {self.nivel_jusante:.2f}m | {bairros}")

    # ---- ações dos agentes ---------------------------------------------

    def iniciar_descarga(self, caudal, duracao, atraso=0):
        """Marca uma descarga já validada pela barragem.

        Args:
            caudal: caudal libertado por ciclo.
            duracao: número de ciclos a descarregar.
            atraso: ciclos de espera antes de abrir as comportas.
        """
        self._descarga = {"caudal": float(caudal), "atraso": int(atraso),
                          "ciclos": int(duracao)}

    def aplicar_mitigacao(self, bairro, recursos):
        """Ativa recursos de mitigação num bairro.

        Cada unidade de um recurso conhecido (ver EFEITO_RECURSO em
        config.py) acrescenta um efeito temporário. Recursos desconhecidos
        são ignorados. Não verifica o estoque: isso é do operador do bairro.

        Args:
            bairro: "A", "B" ou "C".
            recursos: dicionário {recurso: quantidade}.
        """
        alvo = self.bairros[bairro]
        for nome, quantidade in recursos.items():
            efeito = EFEITO_RECURSO.get(nome)
            if efeito is None:
                continue
            for _ in range(int(quantidade)):
                alvo.efeitos.append({"tipo": nome, **efeito})

    # ---- evolução ------------------------------------------------------

    def passo(self):
        """Avança o ambiente um ciclo (ver as regras no topo do ficheiro)."""
        chuva = self.chuva_atual()

        # 1-2. reservatório
        self.caudal_saida = self._caudal_da_descarga()
        self.caudal_entrada = CAUDAL_BASE_ENTRADA + chuva * AREA_BACIA
        variacao = 100.0 * (self.caudal_entrada - self.caudal_saida) / CAPACIDADE_RESERVATORIO
        self.nivel_reservatorio = _limitar(self.nivel_reservatorio + variacao, 0.0, 100.0)

        # 3. rio a jusante
        self.nivel_jusante = NIVEL_JUSANTE_BASE + self.caudal_saida * FATOR_JUSANTE

        # 4-6. bairros
        for b in self.bairros.values():
            entrada = (b.entrada_chuva(chuva)
                       + self.caudal_saida * b.exposicao * (1.0 - b.protecao()))
            novo = _limitar(b.nivel + entrada - b.drenagem(), 0.0, CAPACIDADE_TANQUE)
            b.velocidade = novo - b.nivel
            b.nivel = novo
            b.humidade = _limitar(b.humidade + chuva * HUMIDADE_POR_MM - SECAGEM_SOLO,
                                  0.0, 1.0)
            for e in b.efeitos:
                e["ciclos"] -= 1
            b.efeitos = [e for e in b.efeitos if e["ciclos"] > 0]

        self.chuva_ultimo_ciclo = chuva
        self.ciclo += 1

    def _caudal_da_descarga(self):
        """Caudal a libertar neste ciclo, consumindo um ciclo da descarga.
        Nunca liberta mais água do que o reservatório tem."""
        d = self._descarga
        if d["ciclos"] <= 0:
            return 0.0
        if d["atraso"] > 0:
            d["atraso"] -= 1
            return 0.0
        d["ciclos"] -= 1
        disponivel = self.nivel_reservatorio * CAPACIDADE_RESERVATORIO / 100.0
        return min(d["caudal"], disponivel)
