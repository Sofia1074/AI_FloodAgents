# SPADE: instalação, agentes e behaviours (ISIA PL 1, 2026/27)

Resumo do guia de laboratório `ISIA_01_PL (2026-27).pdf` (SPADE 4.1.4). É a referência do professor para **como escrever agentes e behaviours**. O código do projeto deve seguir este estilo.

## 1. Instalação

Python 3.10 a 3.14. Ambiente virtual, depois `pip install spade` e `spade version` (deve dar 4.1.4).

```
py -m virtualenv spade_venv --python=python3.12
.\spade_venv\Scripts\Activate
pip install --upgrade pip
pip install spade
```

No PowerShell, se o `Activate` for bloqueado: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

Servidor XMPP para desenvolvimento (pyjabber, incluído no SPADE):

- `spade.run(main(), embedded_xmpp_server=True)` lança o servidor dentro do programa (forma preferida). O domínio é `localhost`, por isso os JIDs são do tipo `agente@localhost`.
- Ou `spade run` num terminal à parte (portas 5222 e 5269, página de admin em `http://localhost:9090`). Dá um registo detalhado das mensagens. Nesse caso `spade.run(main())` **não** deve lançar o servidor embutido.

## 2. Agente e behaviours

Um agente SPADE é assíncrono: todo o código corre num ciclo `asyncio`, arrancado com `spade.run(main())`. A programação real do agente faz-se **nos behaviours**.

```python
class DummyAgent(Agent):
    class MyBehav(CyclicBehaviour):
        async def on_start(self):      # antes da 1.ª iteração: inicializações
            self.counter = 0
        async def run(self):           # corpo do ciclo, chamado a cada iteração
            self.counter += 1
            await asyncio.sleep(1)     # nunca bloquear: usar await
        async def on_end(self):        # quando o behaviour termina ou é morto
            ...
    async def setup(self):
        self.add_behaviour(self.MyBehav())
```

- `spade.start_agents(lista)` arranca vários agentes em paralelo. `agent.start(auto_register=True)` regista o JID no servidor.
- `run()` é sempre uma corrotina. **Se houver uma exceção em `on_start`, `run` ou `on_end`, o behaviour é morto sem barulho** e a exceção fica em `exit_code`.
- Terminar um behaviour: `self.kill(exit_code=10)` marca-o para morrer na iteração seguinte (não cancela a iteração em curso: fazer `return`). `behav.is_killed()`, `behav.exit_code`, `await behav.join()` (bloqueante) esperam pelo fim.
- Um agente pode criar outro dentro de um behaviour (`await agent2.start(auto_register=True)`).
- Parar tudo: Ctrl+C. `quit_spade()` está obsoleto.

## 3. Mensagens e templates

Mensagem: `spade.message.Message(to=...)`, com `set_metadata("performative", "inform")` (também `ontology`, `language`), `body` e `thread`. Envia-se com `await self.send(msg)` e recebe-se com `msg = await self.receive(timeout=10)` (devolve `None` no timeout).

**Template**: é como o SPADE entrega cada mensagem recebida ao behaviour que a espera. `add_behaviour(behaviour, template)`. Uma `Template` tem os mesmos atributos que uma `Message` (`to`, `sender`, `body`, `thread`, `metadata`) e **todos** os definidos têm de coincidir. Combinam-se com `&` (E), `|` (OU), `^` (XOR) e `~` (NÃO).

```python
template = Template()
template.set_metadata("performative", "inform")
self.add_behaviour(RecvBehav(), template)
```

Um behaviour sem template recebe todas as mensagens do agente.

## 4. Behaviours avançados

| Behaviour | Quando usar |
|---|---|
| `OneShotBehaviour` | corre `run()` uma só vez |
| `CyclicBehaviour` | repete `run()` sem período (ciclo) |
| `PeriodicBehaviour(period=2, start_at=datetime)` | repete `run()` a cada `period` segundos, opcionalmente a partir de `start_at` |
| `TimeoutBehaviour(start_at=datetime)` | corre uma vez, no instante `start_at` |
| `FSMBehaviour` | máquina de estados finita, para protocolos com várias etapas |

### FSMBehaviour

Contentor (subclasse de `CyclicBehaviour`) com `add_state(name, state, initial=False)` e `add_transition(source, dest)`. Cada estado é uma subclasse de `State` (um `OneShotBehaviour`), com `run()` e, se for preciso, `on_start`/`on_end`, `send` e `receive`.

- Só pode haver **um** estado inicial (fica o último registado).
- Um estado escolhe o seguinte com `self.set_next_state("NOME")`, dentro de `run()`. Um estado que não chama `set_next_state` é final.
- Transição não registada dá `NotValidTransition` e estado não registado dá `NotValidState`. Em ambos o FSM termina.
- **O FSM tem um único template, partilhado por todos os estados**: partilham a mesma fila de mensagens.

```python
fsm = ExampleFSMBehaviour()
fsm.add_state(name="UM", state=StateOne(), initial=True)
fsm.add_state(name="DOIS", state=StateTwo())
fsm.add_transition(source="UM", dest="DOIS")
self.add_behaviour(fsm)
```

## 5. Ligação ao projeto

- Os `PeriodicBehaviour` servem a monitorização; os `CyclicBehaviour` servem a escuta de mensagens; os `FSMBehaviour` servem a negociação da descarga e o Contract Net; o `TimeoutBehaviour` serve o prazo dos votos (ver `gaia_detalhado.md`, secção 9.4).
- A base de conhecimento do agente é `agent.set("chave", valor)` / `agent.get("chave")`.
