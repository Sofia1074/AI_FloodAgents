# Matéria das aulas (ISIA) ligada ao projeto

Resumo dos slides de **ISIA_2** (Intelligent Agents), **ISIA_3** (Multi-Agent Systems),
**ISIA_5** (Social Choice Theory) e **ISIA_6** (Mechanism Design).
O texto completo dos slides está em `docs/aulas/` (só texto: os diagramas e
tabelas dos slides, como o FIPA-ContractNet e a tabela de performativas, não
foram extraídos; ver os PDFs originais).

Em cada secção: **o que a aula diz** → **onde entra no projeto**.

---

## ISIA_2 — Agentes inteligentes

- **Agente** = entidade computacional situada num ambiente, com ação autónoma para cumprir objetivos delegados. Um agente racional escolhe, para cada sequência de perceções, a ação que maximiza a sua medida de desempenho.
- **Propriedades do ambiente**: observável (total/parcial), um/vários agentes, determinístico/estocástico, episódico/sequencial, estático/dinâmico, discreto/contínuo, conhecido/desconhecido.
  → Este projeto: **multiagente, parcialmente observável** (cada operador só vê o seu bairro), **dinâmico** (a água sobe sem os agentes intervirem), **sequencial**, discreto na simulação.
- **Tipos de agente** (capacidade crescente): reflexo simples → reflexo com modelo (estado interno) → baseado em objetivos → baseado em utilidade → com aprendizagem.
  → Operador de bairro ≈ reflexo com modelo (guarda estado e deduz o risco). Líder ≈ baseado em objetivos/utilidade (pesa risco local vs plano). Barragem ≈ baseada em objetivos com restrições de segurança.
- **Propriedades desejáveis** (Wooldridge & Jennings): **reatividade** (responder a tempo a mudanças), **proatividade** (tomar iniciativa) e **capacidade social** (cooperação, coordenação, negociação).
- **BDI (Beliefs-Desires-Intentions)**: crenças = o que o agente sabe; desejos = estados que gostaria de atingir; intenções = o que decidiu perseguir (persistem, são consistentes). Ciclo: rever crenças → gerar opções → filtrar (intenções) → planear → executar → reconsiderar. Estratégias de compromisso: cego, "single-minded", "open-minded".
  → Útil para **descrever** os agentes no relatório (ex.: crença = nível de água; desejo = proteger o bairro; intenção = pedir recursos / votar contra).
- **Agentes reativos / subsumption (Brooks)**: regras situação→ação em camadas, sem representação simbólica; comportamentos de baixo nível têm prioridade.
  → As regras de risco do operador são deste estilo.
- Agentes híbridos = camada reativa + camada deliberativa.

## ISIA_3 — Sistemas multiagente

- **Capacidade social**: **cooperação** (objetivo comum), **coordenação** (gerir interdependências / recursos não partilháveis), **negociação** (acordos com ofertas e contraofertas). Todas exigem comunicação.
- Num agente, outro agente **não pode "invocar um método"**: pede, e o agente decide se faz. ("Objects do it for free, agents do it for money.")
- **Atos de fala** (Austin, Searle): o **performativo** (inform, request, propose…) + o **conteúdo proposicional**. A autonomia do recetor determina o efeito.
- **FIPA-ACL**: mensagem = performativo + parâmetros: `:sender :receiver :content :language :ontology :protocol :conversation-id :reply-with :in-reply-to :reply-by`. Os dois performativos base são **inform** e **request**; os outros definem-se a partir deles.
  Performativos usados no projeto: INFORM, REQUEST, AGREE, REFUSE, CFP, PROPOSE, ACCEPT-PROPOSAL, REJECT-PROPOSAL, FAILURE.
- **Ontologia** = vocabulário partilhado que fixa o significado dos termos (ex.: "risco", "caudal", "bombas", "plano").
- **Protocolos de interação FIPA**: **ContractNet** (gestor anuncia a tarefa/CFP → participantes licitam/propõem → gestor compara e atribui → executante devolve resultado), **FIPA-Request**, **FIPA-Subscribe**.
  → A negociação da barragem (CFP → propostas dos líderes) é um **ContractNet**; `conversation-id` ⇢ `thread` em SPADE.
- **Plataformas**: JADE, Jadex, **SPADE**, Jason… Em JADE/SPADE: 1 agente = comportamentos (behaviours) concorrentes cooperativos; comunicação por mensagens ACL.
- **ABMS (modelação e simulação baseada em agentes)**: modelo = agentes + heurísticas de decisão + topologia de interação + ambiente partilhado; um **escalonador** por ticks/eventos; **recolha de dados e visualização**. O objetivo é observar comportamento coletivo/emergente.
  → O projeto é uma pequena simulação ABMS: deve ter **ticks**, ambiente e **recolha de métricas**.

## ISIA_5 — Teoria da escolha social

- **Escolha social**: agregar preferências de vários agentes numa decisão coletiva. Modelo: conjunto de votantes Ag, conjunto de resultados Ω, cada votante tem uma ordem de preferência sobre Ω.
  - **Função de bem-estar social**: devolve uma ordenação coletiva.
  - **Função de escolha social**: devolve um único resultado.
- **Pluralidade**: ganha quem tem mais primeiros lugares. Com 2 opções = **maioria simples**. Pode eleger o pior para a maioria (paradoxo), e permite **voto tático**.
- **Paradoxo de Condorcet**: com 3+ opções pode não haver vencedor estável (ciclo de maiorias).
- **Maioria sequencial**: depende da **agenda** (ordem dos confrontos) → manipulável.
- **Vencedor de Condorcet**: vence todos os outros em confrontos 2 a 2.
- **Contagem de Borda**: usa a ordem completa (k−posição pontos).
- **Propriedades**: Pareto, vencedor de Condorcet, independência de alternativas irrelevantes (IIA).
- **Teorema de Arrow**: com 3+ opções, só uma ditadura satisfaz Pareto + IIA.
- **Gibbard–Satterthwaite**: todo método não ditatorial é manipulável (um votante pode ganhar mentindo nas preferências).
- **Aplicação ao projeto**:
  - 3 líderes, 1 voto por bairro, maioria simples (2 em 3). Com **uma proposta e 2 opções (sim/não)** é uma eleição par-a-par: não há empates nem ciclos de Condorcet.
  - Se houver **várias propostas**, é preciso escolher o método (pluralidade, maioria sequencial com agenda, Borda…) e justificá-lo com estas propriedades. Com 3 votantes e 3 propostas já pode não haver 2 votos para nenhuma (daí o caso "sem maioria").
  - **Voto tático**: um líder pode exagerar o risco do bairro para obter mais recursos ou impedir uma descarga.
  - A votação **não substitui** a validação técnica da barragem (o operador não vota).

## ISIA_6 — Desenho de mecanismos

- **Desenho de mecanismos** = versão estratégica da escolha social ("teoria da implementação"): desenhar as regras do jogo para que, mesmo com preferências privadas, o comportamento de equilíbrio seja desejável.
- **Leilões** atribuem recursos escassos a quem mais os valoriza. Elementos: leiloeiro e licitantes; valor privado vs comum; protocolo (preço 1.º/2.º, aberto/fechado, rondas).
  - **Inglês** (ascendente aberto), **Holandês** (descendente), **Japonês**, **1.º preço selado**, **Vickrey** (2.º preço selado: estratégia dominante = declarar o valor verdadeiro → *incentive compatible*).
- **Leilões combinatórios**: licitar em **pacotes** de bens; valorizações não aditivas (substitutos/complementares); lanços **OR/XOR**; determinação do vencedor maximiza o bem-estar social (NP-difícil).
- **VCG (Vickrey-Clarke-Groves)**: cada agente paga o custo social que impõe aos outros; é incentive compatible e generaliza o Vickrey.
- **Leilões de dois lados** (double auction, mercado de ordens).
- **Aplicação ao projeto**: os **recursos de mitigação escassos** (bombas, barreiras, equipas) são um problema de afetação. Em vez de a barragem decidir sozinha, pode ver-se como:
  - um **leilão de bens múltiplos / combinatório** em que cada bairro "licita" pelo pacote de recursos que valoriza (o valor pode vir do risco e da população afetada);
  - e **VCG/Vickrey** para incentivar os líderes a declarar o risco verdadeiro (senão, quem exagera fica com os recursos).
  Ligação direta com o texto do trabalho (secção 8.2: "negociar prioridades de recursos limitados").

---

## Como isto deve refletir-se no projeto (checklist)

- [ ] Agentes descritos com a arquitetura certa (reflexo/BDI) e as 3 propriedades: reatividade, proatividade, capacidade social.
- [ ] Mensagens FIPA-ACL com performativo, `thread` (conversation-id) e conteúdo em JSON; vocabulário comum (ontologia) documentado.
- [ ] Negociação da descarga como **ContractNet** (CFP → PROPOSE → ACCEPT/REJECT → resultado).
- [ ] **Votação** com método explícito (maioria simples 2/3) e tratamento de votos em falta, empates e ausência de maioria.
- [ ] **Recursos escassos**: mecanismo de afetação justificado (prioridade, leilão ou VCG) e discussão de manipulação.
- [ ] Simulação com **ticks**, ambiente, cenários e **métricas** (mensagens, rondas, tempo até à decisão, recursos usados, rejeições por segurança).
- [ ] Saída no terminal legível e orientada a eventos (ver abaixo).

## Como deve ser a saída no terminal

Uma simulação por **ticks**; mostrar só o que **muda** e agrupar a negociação num bloco. Exemplo do objetivo:

```
=== Cenário: cheia | reservatório 90% ===
[t=00] estado  A: 10 (baixo)  B: 30 (moderado)  C: 60 (elevado)
[t=01] ALERTA  opB→liderB: moderado | opC→liderC: elevado
[t=01] PEDIDO  liderB pede {bombas:1} | liderC pede {bombas:2, barreiras:1}
[t=02] NEGOCIAÇÃO #1 (reservatório 90% > 80%)
         CFP        barragem → líderes (caudal 40, atraso 0)
         PROPOSE    A: caudal≤80 | B: caudal≤50 | C: caudal≤25, atraso≥2
         Ronda 1    plano {caudal 25, atraso 2} → A sim, B sim, C sim  (3/3) ✔
         Validação  barragem: OK (≤ 80)
         EXECUÇÃO   descarga 25 → reservatório 87.5%
[t=05] estado  A: 35 (moderado)  B: 38 (moderado)  C: 58 (elevado)
...
=== Resumo: 1 negociação | 1 ronda | 12 mensagens | reservatório 90→87.5% ===
```

Regras para evitar ruído: não repetir alertas/pedidos se o risco não mudou; mostrar o estado dos bairros só quando muda; ativar um modo `--verbose` para ver cada mensagem.
