# SPADE-BDI: agentes BDI em AgentSpeak (ISIA PL 1.1, 2026/27)

Resumo do guia `ISIA_01.1_PL (2026-27).pdf`: instalação do plugin `spade_bdi` e o primeiro agente BDI. Os agentes BDI (crenças, desejos, intenções) são matéria de ISIA_2 e este projeto deve usá-los (ver `materia.md`).

## 1. Instalação (sobre SPADE 4.1.4)

```
python -m pip install "spade==4.1.4"
python -m pip install "spade_bdi==0.3.3"
python -m pip uninstall winloop      # só no Windows
```

No Windows o `winloop` pode causar erros assíncronos, de SSL e timeouts. O `spade_bdi` pode reinstalá-lo, por isso remove-se **depois** de o instalar, mesmo que já tenha sido removido antes.

Verificação: `python -m pip show spade_bdi` (versão 0.3.3) e `python -c "from spade_bdi.bdi import BDIAgent; print('BDI OK')"`.

## 2. Primeiro agente BDI

Um agente BDI precisa de um ficheiro Python e de um ficheiro `.asl` (AgentSpeak) com as crenças iniciais, os objetivos e os planos.

`test_agent.asl`:

```
!graduate.                                  // objetivo inicial (desejo)

+!graduate <-                               // plano: ao adotar o objetivo
    .print("Desire adopted: graduate.");
    +ready.                                 // acrescenta a crença ready

+ready <-                                   // plano: quando a crença é acrescentada
    .print("Belief added: ready.").
```

`test_agent.py`:

```python
from spade_bdi.bdi import BDIAgent

async def main():
    agent = BDIAgent("student@localhost", "student_password", "test_agent.asl")
    await agent.start(auto_register=True)
    await asyncio.sleep(3)
    agent.bdi.print_beliefs()          # imprime as crenças atuais
    await agent.stop()

spade.run(main(), embedded_xmpp_server=True)
```

Saída esperada: `Desire adopted: graduate.`, `Belief added: ready.`, e a crença `ready` nas crenças atuais.

## 3. Notas sobre a API do `spade_bdi` 0.3.3

Lidas do código instalado em `.venv/Lib/site-packages/spade_bdi`.

- `BDIAgent(jid, password, asl, actions=None)`. O `BDIAgent` é um `Agent` do SPADE: aceita `add_behaviour` e continua a poder enviar e receber mensagens normais.
- O behaviour BDI (`agent.bdi`) só recebe mensagens com `performative = "BDI"` (as do `.send` do AgentSpeak). As mensagens FIPA normais não lhe chegam.
- Crenças a partir do Python: `agent.bdi.set_belief("risco", "elevado")` (`str` vira átomo), `remove_belief`, `get_belief`, `get_beliefs`, `print_beliefs`. `set_belief` **substitui** as crenças com o mesmo nome e aridade que não unifiquem com a nova, por isso serve para valores únicos (o risco atual), e não para listas de factos.
- Ações próprias em Python: sobrepor `add_custom_actions(self, actions)` e registar com `actions.add_procedure(".nome", (tipos...), funcao)` (ação sem resultado) ou `add_function(...)`. Dentro do `.asl` usam-se como `.nome(...)`. Para enviar uma mensagem a partir de uma ação (código síncrono) usa-se `self.submit(self.bdi.send(msg))`.
- Os átomos do AgentSpeak começam por minúscula e não aceitam acentos (usar `critico`, não `crítico`). Os textos entre aspas também não devem levar acentos: o `spade_bdi` abre o `.asl` com a codificação do sistema (cp1252 no Windows) e um "ê" estraga-se, o que faz o plano falhar ao imprimir. Nos comentários (`//`) os acentos não fazem mal.
- `agent.pause_bdi()` e `agent.resume_bdi()` suspendem e retomam o ciclo BDI.

## 4. Como o BDI entra no projeto

Ver `agentes/lider.py` e `agentes/lider.asl`. O líder comunitário passa a ser um `BDIAgent`:

- **Crenças:** o risco do bairro (do operador), a proposta de descarga em análise, o caudal que cada risco permite e os recursos que cada risco exige.
- **Desejos/objetivos:** `!proteger_bairro`, e `!mitigar(Risco)` quando o risco sobe.
- **Intenções/planos:** pedir recursos ao operador; aceitar, contrapropor ou rejeitar uma descarga.
- O envio e a receção das mensagens FIPA continuam a ser feitos pelos behaviours do SPADE. O `.asl` só decide, e as ações em Python executam.
