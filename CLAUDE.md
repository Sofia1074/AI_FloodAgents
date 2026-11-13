# Projeto SA — Alerta Precoce e Resposta a Inundações Urbanas (SPADE)

Trabalho académico (3.º ano). Comunicar com o utilizador em **português**.

## Guia oficial do projeto

O guia é o PDF **"Arquitetura Multiagente para um Sistema Descentralizado de Alerta Precoce e Resposta a Inundações Urbanas.pdf"** (versão de 2026-11-12, com a metodologia Gaia). Está na pasta da disciplina, um nível acima deste repo. O texto equivalente em Markdown está em `docs/arquitetura_gaia.md`.

Se o código ou este ficheiro divergirem do guia, o guia manda. Apontar a divergência à equipa antes de mudar seja o que for.

O resumo abaixo serve para consulta rápida. Em caso de dúvida, ler o guia.

### Agentes e papéis Gaia (8 agentes, sem entidade central)

| Agente | Função | Papéis Gaia |
|---|---|---|
| 1 — Operador da Barragem | Monitoriza o reservatório, propõe descargas, valida a segurança, executa. Não vota. | OperadorBarragem, CoordenadorVotacao |
| 2A, 2B, 2C — Operadores dos Bairros | Monitorizam o bairro, avaliam o risco (baixo, moderado, elevado, crítico), controlam o estoque físico, executam serviços contratados | MonitorBairro, ExecutorLocal |
| 3A, 3B, 3C — Líderes Comunitários | Representam o bairro, negociam e votam, gerem a moeda, contratam ou oferecem serviços | RepresentanteBairro, Comprador, Fornecedor |
| 4 — Diretório de Serviços | Guarda e fornece ofertas (serviço, preço, fornecedor, disponibilidade). Não decide. | Diretorio |

A estrutura organizacional está na Figura 1 do guia (`docs/gaia_estrutura.png`). A versão longa do modelo Gaia (ambiente, vivacidade e segurança, serviços, correspondência com o SPADE) está em `docs/gaia_detalhado.md`.

### Regras principais

- Negociação da descarga: a barragem propõe caudal, horário e duração. Os líderes aceitam, rejeitam ou propõem alternativa. Várias rodadas, até um máximo. Sem acordo, contingência.
- Votação, implementada à parte da negociação: 3 líderes, 1 voto cada, aprovação com 2 em 3. Depois da aprovação, a barragem valida a segurança. A votação nunca autoriza uma operação insegura.
- Contratação entre bairros com FIPA Contract Net, iniciada pelo líder comprador: CFP, propostas, aceitar, rejeitar ou contrapropor, reserva, execução pelo operador do bairro fornecedor, pagamento só após confirmação. Falha liberta a reserva sem pagamento.
- Preços base fictícios: sacos de areia (lote) 10, bomba 20, equipa 30. O comprador abre com cerca de 60% do preço base; o vendedor aceita a partir de 70%, senão contrapropõe.
- Um bairro só oferece recursos se mantiver uma reserva mínima.
- Performativas FIPA-ACL: INFORM, REQUEST, AGREE/REFUSE, CFP, PROPOSE, ACCEPT-PROPOSAL/REJECT-PROPOSAL, FAILURE. Cada mensagem leva identificador da negociação e, quando aplicável, da proposta.

### Cenários de avaliação (secção 7 do guia)

1. Risco elevado num bairro: subida rápida da água, o líder pede mitigação.
2. Conflito de interesses: os bairros divergem sobre a descarga, com negociação e votação.
3. Recursos limitados: um bairro contrata um recurso de outro bairro.

## Estado do código (resumo)

- Executar com um Python que tenha o SPADE: `python main.py [cenário] [-v]`. Cenários: `risco_elevado` (por omissão), `conflito`, `recursos_limitados`, e os de teste `calmo` e `cheia`. `-v` mostra cada mensagem e cada ciclo do ambiente. Na máquina da Telma o SPADE está no `spade_venv` da pasta da disciplina (Python 3.13, SPADE 4.1.4).
- Testes (não precisam de SPADE): `python -m unittest discover -s tests -v`.
- `metricas.py`: recolhe as métricas da secção 7 do guia (deteção, mensagens, tempo até à decisão, recursos, risco por ciclo, propostas, transações). `main.py` grava tudo em `resultados/<cenário>/` (ciclos.csv, eventos.csv, resumo.json). Os agentes chamam ganchos (`metricas.alerta`, `metricas.mitigacao`, `metricas.proposta`, `metricas.decisao`, `metricas.rejeitada_seguranca`, `metricas.descarga`, `metricas.transacao`); quem mexer na barragem ou no Contract Net deve manter ou acrescentar estas chamadas. As mensagens contam-se sozinhas (embrulho no `send` do SPADE).
- `graficos.py`: lê `resultados/` e desenha os PNG para os slides (nível dos bairros com faixas de risco, reservatório e descargas) e `resultados/resumo_cenarios.csv`. Precisa de matplotlib, não de SPADE. A pasta `resultados/` não vai para o git.
- `ambiente.py`: o mundo simulado (reservatório, chuva, rio a jusante, bairros com humidade e drenagem, efeitos da mitigação). Avança um ciclo a cada `PERIODO_CICLO` segundos (`main.py`). Os agentes leem e alteram o ambiente; não guardam níveis próprios. As limitações do modelo estão documentadas no topo do ficheiro.
- `registo.py`: saída do terminal. `evento()` mostra sempre (ALERTA, MITIGAÇÃO, VOTAÇÃO, DESCARGA, com o tempo `[t=..s]`); `detalhe()` só com `-v`. Usar estas funções em vez de `print` nos agentes. Os operadores só alertam quando o risco **muda**.
- `config.py`: constantes e `jid()`. `rede.py`: matriz de adjacências (`REDE`).
- `agentes/`: `barragem.py` (DamOperator), `operador.py` (NeighbourhoodOperator), `lider.py` (CommunityLeader). Ainda não existe o Agente 4 (Diretório).
- `cenarios.py`: só dados (estado inicial, chuva por ciclo, características, estoque e moeda de cada bairro). Tem os três cenários do guia e os de teste "calmo" e "cheia". O cenário `recursos_limitados` só fica completo com o estoque e o Contract Net (hoje o bairro B ainda se mitiga sozinho).
- `main.py`: ponto de entrada.
- Ainda não implementado: Diretório, Contract Net, moeda e estoque, negociação em várias rodadas, votação separada, contingência, controlo de estoque pelo operador (os recursos de mitigação ainda são ilimitados).
- Bugs conhecidos por corrigir: corrida no arranque (operadores alertam antes de os líderes arrancarem), a barragem pode contar mensagens que não são votos, contrapropostas dos líderes nunca usadas, `json.loads` sem tratamento de erros.

## Matéria das aulas (referência obrigatória)

O trabalho deve refletir a matéria de ISIA. Resumo e ligação ao projeto em
`docs/materia.md`; texto completo dos slides em `docs/aulas/` (ISIA_2 Agentes
Inteligentes, ISIA_3 Sistemas Multiagente/FIPA/ContractNet, ISIA_5 Escolha
Social/votação, ISIA_6 Desenho de Mecanismos/leilões/VCG). Ao mudar o código,
justificar as escolhas com estes conceitos (BDI/tipos de agente, FIPA-ACL e
ContractNet, método de votação, afetação de recursos escassos) e manter a saída
do terminal curta e orientada a eventos (ver `docs/materia.md`).

## Entregáveis

- Código Python (SPADE).
- Documentação em HTML gerada a partir de comentários especiais no código (docstrings). Ferramenta a confirmar com o professor.
- Slides de apresentação.
