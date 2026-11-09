"""
Cada classe diz o que o agente TEM (atributos) e o que vai FAZER (métodos).
Agora cada classe é um agente SPADE (herda de Agent) com o seu JID no servidor XMPP.
"""

import json

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message


DOMINIO = "localhost"
PASSWORD = "password"


def jid(nome):
    return f"{nome}@{DOMINIO}"


# ---------------------------------------------------------------------------
# Rede de relações entre agentes (matriz de adjacências)
# ---------------------------------------------------------------------------

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

# Parâmetros da barragem
NIVEL_ALERTA_RESERVATORIO = 80.0   # % a partir da qual é preciso descarregar
CAPACIDADE_RESERVATORIO = 10000.0  # volume que corresponde a 100% de enchimento
PERIODO_MONITORIZACAO = 10         # segundos entre verificações do reservatório
TEMPO_ESPERA_VOTOS = 3             # segundos à espera da resposta dos líderes

# Parâmetros dos bairros
PERIODO_MEDICAO = 5                # segundos entre medições do operador de bairro
CAPACIDADE_TANQUE = 100.0          # nível de água que o bairro consegue reter
FATOR_CHEIA = 1.0                  # quanto o nível sobe por cada unidade de caudal libertado
# nível de água (%) até ao qual cada risco se aplica; acima de 75 é "crítico"
LIMITES_RISCO = [(25.0, "baixo"), (50.0, "moderado"), (75.0, "elevado")]
# efeito de cada recurso a reduzir o nível de água do bairro
EFEITO_RECURSO = {"bombas": 5.0, "barreiras": 3.0, "equipas": 2.0}
# recursos que o líder pede, conforme o risco do bairro
RECURSOS_POR_RISCO = {
    "baixo": {},
    "moderado": {"bombas": 1},
    "elevado": {"bombas": 2, "barreiras": 1},
    "crítico": {"bombas": 3, "barreiras": 2, "equipas": 1},
}
# caudal máximo que o líder aceita da barragem, conforme o risco do bairro
CAUDAL_ACEITE = {"baixo": 80.0, "moderado": 50.0, "elevado": 25.0, "crítico": 0.0}


class DamOperator(Agent):
    """Agente 1 — Operador da Barragem (existe um só)."""

    def __init__(self, nome, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.nivel_reservatorio = 0.0    # % de enchimento do reservatório
        self.caudal_descarga = 0.0       # caudal que está a ser libertado
        self.caudal_maximo_seguro = 80.0 # limite operacional das comportas

    class Monitorizar(PeriodicBehaviour):
        """De tempos a tempos: avalia o reservatório e, se for preciso,
        propõe o plano aos líderes, conta os votos e executa a descarga."""

        async def run(self):
            dam = self.agent
            if not dam.avaliar_descarga():
                return

            plano = dam.propor_plano()
            if not dam.validar_plano(plano):
                return

            # 1) propor o plano aos líderes com quem a rede permite falar
            lideres = [f"lider{b}" for b in "ABC"
                       if dam.rede.pode_comunicar(dam.nome, f"lider{b}")]
            for lider in lideres:
                msg = Message(to=jid(lider))
                msg.set_metadata("performative", "propose")
                msg.body = json.dumps(plano)
                await self.send(msg)
            print(f"[{dam.nome}] plano proposto: {plano}", flush=True)

            # 2) recolher os votos (quem não responde a tempo conta como "não")
            votos = {}
            while len(votos) < len(lideres):
                resposta = await self.receive(timeout=TEMPO_ESPERA_VOTOS)
                if resposta is None:
                    break
                aceitou = resposta.get_metadata("performative") == "accept-proposal"
                votos[resposta.sender.user] = aceitou
            print(f"[{dam.nome}] votos: {votos}", flush=True)

            # 3) maioria aprova -> executa e informa os operadores de bairro
            if sum(votos.values()) > len(lideres) / 2:
                dam.executar_descarga(plano)
                print(f"[{dam.nome}] descarga executada, reservatório a "
                      f"{dam.nivel_reservatorio:.1f}%", flush=True)
                for b in "ABC":
                    if dam.rede.pode_comunicar(dam.nome, f"op{b}"):
                        info = Message(to=jid(f"op{b}"))
                        info.set_metadata("performative", "inform")
                        info.body = json.dumps(plano)
                        await self.send(info)
            else:
                print(f"[{dam.nome}] plano rejeitado, nada foi executado", flush=True)

    async def setup(self):
        print(f"[{self.nome}] agente ativo", flush=True)
        self.add_behaviour(self.Monitorizar(period=PERIODO_MONITORIZACAO))

    def avaliar_descarga(self):
        """Decide se é preciso fazer uma descarga.
        Há descarga quando o reservatório passa o nível de alerta."""
        return self.nivel_reservatorio > NIVEL_ALERTA_RESERVATORIO

    def propor_plano(self):
        """Cria um plano de descarga (caudal, atraso, duração).
        O plano é um dicionário. Quanto mais cheio o reservatório, maior o
        caudal proposto (nunca acima do máximo seguro). Sem necessidade de
        descarga devolve None."""
        if not self.avaliar_descarga():
            return None

        # fração do "espaço de risco" já ocupada: 0.0 no nível de alerta, 1.0 a 100%
        excesso = (self.nivel_reservatorio - NIVEL_ALERTA_RESERVATORIO) / (
            100.0 - NIVEL_ALERTA_RESERVATORIO)
        excesso = min(excesso, 1.0)

        return {
            "caudal": round(self.caudal_maximo_seguro * excesso, 1),
            "atraso": 0,       # passos de simulação até começar
            "duracao": 10,     # passos de simulação a descarregar
        }

    def validar_plano(self, plano):
        """Verifica se um plano respeita os limites de segurança."""
        if plano is None:
            return False
        return (0 < plano["caudal"] <= self.caudal_maximo_seguro
                and plano["atraso"] >= 0
                and plano["duracao"] > 0)

    def executar_descarga(self, plano):
        """Abre as comportas segundo um plano já validado.
        Regista o caudal e baixa o nível do reservatório pelo volume
        libertado (caudal x duração)."""
        self.caudal_descarga = plano["caudal"]
        volume = plano["caudal"] * plano["duracao"]
        self.nivel_reservatorio = max(
            0.0, self.nivel_reservatorio - 100.0 * volume / CAPACIDADE_RESERVATORIO)


class NeighbourhoodOperator(Agent):
    """Agentes 2A, 2B, 2C — Operador de um bairro."""

    def __init__(self, nome, bairro, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.bairro = bairro             # "A", "B" ou "C"
        self.nivel_agua = 0.0            # nível da água no bairro
        self.tanque_livre = CAPACIDADE_TANQUE   # capacidade de retenção disponível
        self.risco = "baixo"             # baixo, moderado, elevado ou crítico
        self.ultimo_risco_enviado = None # para só alertar quando há novidade

    class Monitorizar(PeriodicBehaviour):
        """De tempos a tempos: mede, avalia o risco e alerta o líder."""

        async def run(self):
            op = self.agent
            op.medir()
            op.avaliar_risco()

            # só alerta se o risco não for baixo ou se mudou desde o último alerta
            if op.risco == "baixo" and op.risco == op.ultimo_risco_enviado:
                return
            lider = f"lider{op.bairro}"
            if not op.rede.pode_comunicar(op.nome, lider):
                return

            alerta = op.alertar_lider()
            msg = Message(to=jid(lider))
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps(alerta)
            await self.send(msg)
            op.ultimo_risco_enviado = op.risco
            print(f"[{op.nome}] alerta enviado: risco {op.risco} "
                  f"(nível {op.nivel_agua:.1f})", flush=True)

    class OuvirMensagens(CyclicBehaviour):
        """Recebe: pedidos de recursos do líder e avisos de descarga da barragem."""

        async def run(self):
            op = self.agent
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            origem = msg.sender.user
            conteudo = json.loads(msg.body)
            performative = msg.get_metadata("performative")

            if origem.startswith("lider") and performative == "request":
                op.ativar_mitigacao(conteudo["recursos"])
                print(f"[{op.nome}] mitigação ativada {conteudo['recursos']} "
                      f"-> nível {op.nivel_agua:.1f}", flush=True)
            elif origem == "barragem" and performative == "inform":
                # a água libertada pela barragem chega ao bairro
                op.nivel_agua = min(CAPACIDADE_TANQUE,
                                    op.nivel_agua + conteudo["caudal"] * FATOR_CHEIA)
                print(f"[{op.nome}] descarga a chegar (caudal {conteudo['caudal']}) "
                      f"-> nível {op.nivel_agua:.1f}", flush=True)

    async def setup(self):
        print(f"[{self.nome}] agente ativo (bairro {self.bairro})", flush=True)
        self.add_behaviour(self.Monitorizar(period=PERIODO_MEDICAO))
        self.add_behaviour(self.OuvirMensagens())

    def medir(self):
        """Lê os sensores do bairro.
        O nível de água é atualizado de fora (avisos da barragem, mitigação);
        aqui calcula-se o que se deduz dele: a capacidade de retenção livre."""
        self.tanque_livre = max(0.0, CAPACIDADE_TANQUE - self.nivel_agua)
        return self.nivel_agua, self.tanque_livre

    def avaliar_risco(self):
        """Calcula o nível de risco a partir das medições."""
        self.risco = "crítico"
        for limite, risco in LIMITES_RISCO:
            if self.nivel_agua < limite:
                self.risco = risco
                break
        return self.risco

    def alertar_lider(self):
        """Prepara o alerta com o risco e os dados, para enviar ao líder
        do bairro (o envio é feito pelo behaviour Monitorizar)."""
        return {
            "bairro": self.bairro,
            "risco": self.risco,
            "nivel_agua": self.nivel_agua,
            "tanque_livre": self.tanque_livre,
        }

    def ativar_mitigacao(self, recursos):
        """Liga bombas, barreiras ou equipas no bairro.
        Cada recurso baixa o nível de água conforme o seu efeito."""
        reducao = sum(EFEITO_RECURSO.get(nome, 0.0) * qtd
                      for nome, qtd in recursos.items())
        self.nivel_agua = max(0.0, self.nivel_agua - reducao)
        self.medir()


class CommunityLeader(Agent):
    """Agentes 3A, 3B, 3C — Líder comunitário de um bairro."""

    def __init__(self, nome, bairro, password=PASSWORD):
        super().__init__(jid(nome), password)
        self.nome = nome
        self.rede = REDE                 # quem comunica com quem
        self.bairro = bairro
        self.risco_do_bairro = "baixo"   # último risco recebido do operador
        self.recursos_pedidos = {}       # bombas, barreiras, equipa...

    class OuvirMensagens(CyclicBehaviour):
        """Recebe alertas do operador do bairro e propostas da barragem."""

        async def run(self):
            lider = self.agent
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            origem = msg.sender.user
            conteudo = json.loads(msg.body)
            performative = msg.get_metadata("performative")

            if origem.startswith("op") and performative == "inform":
                # alerta do operador -> pede recursos de volta, se for preciso
                pedidos = lider.receber_alerta(conteudo)
                destino = f"op{lider.bairro}"
                if pedidos and lider.rede.pode_comunicar(lider.nome, destino):
                    pedido = Message(to=jid(destino))
                    pedido.set_metadata("performative", "request")
                    pedido.body = json.dumps({"recursos": pedidos})
                    await self.send(pedido)
                    print(f"[{lider.nome}] risco {lider.risco_do_bairro}: "
                          f"pediu recursos {pedidos}", flush=True)

            elif origem == "barragem" and performative == "propose":
                # proposta da barragem -> vota (e, se recusar, contrapropõe)
                if not lider.rede.pode_comunicar(lider.nome, "barragem"):
                    return
                resposta = lider.propor(conteudo)
                voto = Message(to=jid("barragem"))
                voto.set_metadata(
                    "performative",
                    "accept-proposal" if resposta["aceita"] else "reject-proposal")
                voto.body = json.dumps(resposta)
                await self.send(voto)
                print(f"[{lider.nome}] {'aceitou' if resposta['aceita'] else 'recusou'} "
                      f"o plano (risco {lider.risco_do_bairro})", flush=True)

    async def setup(self):
        print(f"[{self.nome}] agente ativo (bairro {self.bairro})", flush=True)
        self.add_behaviour(self.OuvirMensagens())

    def receber_alerta(self, alerta):
        """Interpreta o alerta enviado pelo operador do bairro.
        Guarda o risco e decide os recursos a pedir (devolve-os)."""
        self.risco_do_bairro = alerta["risco"]
        self.recursos_pedidos = dict(RECURSOS_POR_RISCO[self.risco_do_bairro])
        return self.recursos_pedidos

    def propor(self, plano_da_barragem):
        """Responde à barragem com condições ou uma contraproposta.
        Se aceita, devolve só o voto. Se recusa, propõe o caudal máximo que o
        bairro aguenta (ou nenhuma contraproposta se não aguenta descarga)."""
        if self.votar(plano_da_barragem):
            return {"aceita": True, "contraproposta": None}

        limite = CAUDAL_ACEITE[self.risco_do_bairro]
        contraproposta = None
        if limite > 0:
            contraproposta = dict(plano_da_barragem, caudal=limite)
        return {"aceita": False, "contraproposta": contraproposta}

    def votar(self, plano):
        """Decide se aprova ou rejeita um plano:
        aprova se o caudal couber no que o risco do bairro permite."""
        return plano["caudal"] <= CAUDAL_ACEITE[self.risco_do_bairro]


async def main():
    # Cria e arranca os 7 agentes só para ver que estão ligados ao servidor
    barragem = DamOperator("barragem")
    operadores = [NeighbourhoodOperator(f"op{b}", b) for b in "ABC"]
    lideres = [CommunityLeader(f"lider{b}", b) for b in "ABC"]
    todos = [barragem, *operadores, *lideres]

    for agente in todos:
        await agente.start(auto_register=True)
    print("7 agentes ativos", flush=True)

    for agente in todos:
        await agente.stop()


if __name__ == "__main__":
    spade.run(main(), embedded_xmpp_server=True)
