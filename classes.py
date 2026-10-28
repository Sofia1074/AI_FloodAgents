"""Passo 1: esqueleto das classes do sistema (Python simples, ainda sem SPADE).

Cada classe diz o que o agente TEM (atributos) e o que vai FAZER (métodos).
Os métodos ainda não têm lógica: só descrevem o que farão mais tarde.
"""


class DamOperator:
    """Agente 1 — Operador da Barragem (existe um só)."""

    def __init__(self, nome):
        self.nome = nome
        self.nivel_reservatorio = 0.0    # % de enchimento do reservatório
        self.caudal_descarga = 0.0       # caudal que está a ser libertado
        self.caudal_maximo_seguro = 80.0 # limite operacional das comportas

    def avaliar_descarga(self):
        """Decide se é preciso fazer uma descarga."""
        pass

    def propor_plano(self):
        """Cria um plano de descarga (caudal, atraso, duração)."""
        pass

    def validar_plano(self, plano):
        """Verifica se um plano respeita os limites de segurança."""
        pass

    def executar_descarga(self, plano):
        """Abre as comportas segundo um plano já validado."""
        pass


class NeighbourhoodOperator:
    """Agentes 2A, 2B, 2C — Operador de um bairro."""

    def __init__(self, nome, bairro):
        self.nome = nome
        self.bairro = bairro             # "A", "B" ou "C"
        self.nivel_agua = 0.0            # nível da água no bairro
        self.tanque_livre = 0.0          # capacidade de retenção disponível
        self.risco = "baixo"             # baixo, moderado, elevado ou crítico

    def medir(self):
        """Lê os sensores do bairro."""
        pass

    def avaliar_risco(self):
        """Calcula o nível de risco a partir das medições."""
        pass

    def alertar_lider(self):
        """Envia o risco e os dados ao líder comunitário do bairro."""
        pass

    def ativar_mitigacao(self, recursos):
        """Liga bombas, barreiras ou equipas no bairro."""
        pass


class CommunityLeader:
    """Agentes 3A, 3B, 3C — Líder comunitário de um bairro."""

    def __init__(self, nome, bairro):
        self.nome = nome
        self.bairro = bairro
        self.risco_do_bairro = "baixo"   # último risco recebido do operador
        self.recursos_pedidos = {}       # bombas, barreiras, equipa...

    def receber_alerta(self, alerta):
        """Interpreta o alerta enviado pelo operador do bairro."""
        pass

    def propor(self, plano_da_barragem):
        """Responde à barragem com condições ou uma contraproposta."""
        pass

    def votar(self, plano):
        """Decide se aprova ou rejeita um plano."""
        pass


if __name__ == "__main__":
    # Cria os 7 agentes só para ver que as classes funcionam
    barragem = DamOperator("barragem")
    operadores = [NeighbourhoodOperator(f"op{b}", b) for b in "ABC"]
    lideres = [CommunityLeader(f"lider{b}", b) for b in "ABC"]

    for agente in [barragem, *operadores, *lideres]:
        print("criado:", agente.nome)
