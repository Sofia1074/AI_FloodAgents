"""Rede de relações entre agentes (matriz de adjacências)."""

# A ORDEM desta lista define a linha/coluna de cada agente na matriz.
AGENTES = ["barragem",
           "opA", "opB", "opC",
           "liderA", "liderB", "liderC"]


class RedeRelacoes:
    """Quem pode comunicar com quem (matriz de adjacências).

    matriz[i][j] == 1  ->  o agente i pode enviar mensagens ao agente j
    matriz[i][j] == 0  ->  não pode
    """

    def __init__(self):
        n = len(AGENTES)
        self.matriz = [[0] * n for _ in range(n)]

        for b in "ABC":
            self.ligar(f"op{b}", f"lider{b}")       # operador <-> líder do seu bairro
            self.ligar(f"lider{b}", f"op{b}")
            self.ligar("barragem", f"lider{b}")     # barragem <-> líderes
            self.ligar(f"lider{b}", "barragem")
            self.ligar("barragem", f"op{b}")        # barragem -> operadores (só um sentido)

    def ligar(self, origem, destino):
        """Permite que 'origem' envie mensagens a 'destino'."""
        self.matriz[AGENTES.index(origem)][AGENTES.index(destino)] = 1

    def pode_comunicar(self, origem, destino):
        """True se 'origem' pode enviar mensagens a 'destino'."""
        return self.matriz[AGENTES.index(origem)][AGENTES.index(destino)] == 1


# Rede partilhada por todos os agentes
REDE = RedeRelacoes()
