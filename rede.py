"""Rede de relações entre agentes (matriz de adjacências)."""

# A ORDEM desta lista define a linha/coluna de cada agente na matriz.
AGENTES = ["barragem",
           "opA", "opB", "opC",
           "liderA", "liderB", "liderC",
           "diretorio"]


class RedeRelacoes:
    """Quem pode comunicar com quem (matriz de adjacências).

    matriz[i][j] == 1  ->  o agente i pode enviar mensagens ao agente j
    matriz[i][j] == 0  ->  não pode

    As ligações seguem a Figura 1 do guia:

    - operador <-> líder do mesmo bairro (alertas, mitigação, execução de
      serviços contratados);
    - barragem <-> líderes (negociação e votação) e barragem -> operadores
      (aviso de descarga, só num sentido);
    - líder <-> líder, todos com todos: o Contract Net pode ligar quaisquer
      dois líderes, não só os vizinhos na figura;
    - líder <-> diretório (publicar e consultar ofertas).

    Attributes:
        matriz (list[list[int]]): A matriz de adjacências, pela ordem de AGENTES.
    """

    def __init__(self):
        """Cria a matriz com as ligações da Figura 1 do guia."""
        n = len(AGENTES)
        self.matriz = [[0] * n for _ in range(n)]

        for b in "ABC":
            self.ligar(f"op{b}", f"lider{b}")       # operador <-> líder do seu bairro
            self.ligar(f"lider{b}", f"op{b}")
            self.ligar("barragem", f"lider{b}")     # barragem <-> líderes
            self.ligar(f"lider{b}", "barragem")
            self.ligar("barragem", f"op{b}")        # barragem -> operadores (só um sentido)
            self.ligar(f"lider{b}", "diretorio")    # líder <-> diretório
            self.ligar("diretorio", f"lider{b}")
            for outro in "ABC":                     # líder <-> líder (Contract Net)
                if outro != b:
                    self.ligar(f"lider{b}", f"lider{outro}")

    def _indice(self, nome):
        """Linha/coluna de um agente na matriz.

        Aceita o nome com qualquer capitalização ("liderA" ou "lidera"),
        porque o remetente de uma mensagem chega em minúsculas (JID).

        Args:
            nome (str): Nome do agente.

        Returns:
            int: Posição do agente em AGENTES.

        Raises:
            ValueError: Se o agente não existir.
        """
        for i, agente in enumerate(AGENTES):
            if agente.lower() == nome.lower():
                return i
        raise ValueError(f"agente desconhecido: {nome!r}")

    def ligar(self, origem, destino):
        """Permite que 'origem' envie mensagens a 'destino'.

        Args:
            origem (str): Nome do agente que envia.
            destino (str): Nome do agente que recebe.
        """
        self.matriz[self._indice(origem)][self._indice(destino)] = 1

    def pode_comunicar(self, origem, destino):
        """True se 'origem' pode enviar mensagens a 'destino'.

        Args:
            origem (str): Nome do agente que envia.
            destino (str): Nome do agente que recebe.

        Returns:
            bool: Se a ligação existe na matriz.
        """
        return self.matriz[self._indice(origem)][self._indice(destino)] == 1


# Rede partilhada por todos os agentes
REDE = RedeRelacoes()
