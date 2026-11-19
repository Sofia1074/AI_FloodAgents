# Resultados dos cenários finais (para os slides)

Uma execução de cada cenário, com o código atual (reservatório só recebe água
da chuva; `conflito` com o reservatório a 96%). 24 a 25 ciclos de 2 s (cerca de
50 s de simulação). Os valores variam um pouco entre execuções.
Dados completos: `resultados/<cenário>/` (`resumo.json`, `eventos.csv`, `ciclos.csv`)
e `resultados/resumo_cenarios.csv`. Gráficos em `resultados/<cenário>/*.png`.

## Tabela principal

| | 1. Risco elevado | 2. Conflito / emergência | 3. Recursos limitados | Teste "cheia" |
|---|---|---|---|---|
| Situação inicial | reservatório 55%; A, B, C baixo | reservatório **96%**; A elevado, B baixo, C moderado | reservatório 60%; B elevado, sem bombas | reservatório 90%; C elevado |
| Deteção (ciclos até ao alerta) | A: 0, B: 0 | A: 0, B: 3, C: 4 | B: 0 | C: 0 |
| Mensagens trocadas | 24 | 40 | 33 | 33 |
| Alertas de risco | 10 | 12 | 7 | 6 |
| Pior risco (A / B / C) | crítico / elevado / moderado | crítico / elevado / elevado | moderado / elevado / baixo | baixo / moderado / elevado |
| Ciclos em risco elevado ou crítico (A / B / C) | 8 / 3 / 0 | 11 / 8 / 5 | 0 / 9 / 0 | 0 / 0 / 2 |
| Nível máx. de água (A / B / C) | 51,5 / 29,5 / 20,7 | 55,0 / 31,8 / 35,0 | 21,1 / 50,0 / 9,4 | 10,0 / 30,0 / 60,0 |
| Risco final (A / B / C) | baixo / baixo / baixo | baixo / baixo / baixo | baixo / baixo / baixo | baixo / baixo / baixo |
| Recursos de mitigação ativados | 13 (8 bombas, 4 barreiras, 1 equipa) | 20 (13 bombas, 6 barreiras, 1 equipa) | 4 (3 bombas, 1 barreira) | 5 (4 bombas, 1 barreira) |
| Descargas da barragem | 0 (reservatório fica 55 a 58%) | 1, de **contingência** (emergência): caudal 60, 20 ciclos, sem votação | 0 | 1 normal: caudal 40, 20 ciclos |
| Votação | não houve | não houve (a emergência dispensa-a) | não houve | 2 em 3, aprovada |
| Reservatório (início / fim) | 55,0 / 58,5% | 96,0 / 75,4% | 60,0 / 62,0% | 90,0 / 74,0% |
| Contratos entre bairros | 0 | 0 | **1**: B compra 2 bombas a A por 14 cada | 0 |

## O que cada cenário mostra

1. **Risco elevado:** a resposta é toda local. O operador deteta a subida do A
   no ciclo 0, o líder pede mitigação, e sem intervenção da barragem os três
   bairros voltam a risco baixo em cerca de 15 ciclos.
2. **Conflito / emergência:** com o reservatório a 96% a barragem aplica a
   contingência (75% do caudal máximo seguro) sem negociar nem votar, e baixa o
   reservatório para 75%. Os bairros A e B chegam a crítico e elevado, mas
   recuperam. Mostra a regra "a segurança não espera por acordo".
3. **Recursos limitados:** o B, em risco elevado e sem bombas, usa o Contract
   Net: CFP, 5 propostas, 1 aceite e 1 rejeitada, e paga a A **14 por bomba**
   (70% do preço base de 20, o mínimo que o vendedor aceita). Recupera para
   risco baixo no ciclo 24.
4. **Cheia (teste):** é a única execução com votação normal: a barragem propõe
   40, aprovada por 2 em 3, e executa depois de validar a segurança.

## Conclusões

- A resposta é **descentralizada**: sem entidade central, os bairros e a
  barragem detetam, mitigam e decidem por mensagens FIPA-ACL.
- A **deteção é rápida**: 0 a 4 ciclos (0 a 8 s) nos quatro cenários.
- **Votação**, **contingência** e **Contract Net** funcionam, cada um no seu
  cenário, e terminam com todos os bairros em risco baixo.
- Há um **compromisso**: descarregar protege o reservatório mas aumenta a
  água nos bairros expostos (o A, junto ao rio).

## Ressalvas (dizer na apresentação ou resolver antes)

- São **execuções únicas** e não determinísticas; não há comparação de
  parâmetros (falta `resultados/experimentos/comparacao.csv`).
- **A negociação em várias rodadas não aparece** em nenhum cenário final: no
  cenário de teste "cheia" a negociação acaba na rodada 1 (2 em 3 aceitam
  logo) e no `conflito` a emergência dispensa-a.
- A métrica "tempo até à decisão" dá 0 ms por causa do relógio do Windows
  (`time.monotonic`, 15,6 ms); o valor real ronda 5 ms.
- A contingência por emergência não conta como "proposta" nas métricas
  (aparece "propostas 0" mas "descargas 1").
- `resultados/resumo_cenarios.csv` ainda inclui uma pasta antiga
  (`emergencia`) que já não é um cenário.
