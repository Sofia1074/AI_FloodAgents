# Projeto SA — Alerta Precoce e Resposta a Inundações Urbanas (SPADE)

Trabalho académico (3.º ano). Comunicar com o utilizador em **português**.

## Estado do código (resumo)

- Executar com **Python 3.12** (é o único com SPADE instalado): `py -3.12 main.py`
- `config.py`: constantes e `jid()`. `rede.py`: matriz de adjacências (`REDE`).
- `agentes/`: `barragem.py` (DamOperator), `operador.py` (NeighbourhoodOperator), `lider.py` (CommunityLeader).
- `cenarios.py`: só dados (estado inicial). Por agora só existe o cenário "calmo"; faltam os cenários descritos na secção 14 do contexto abaixo.
- `main.py`: ponto de entrada.
- `sistema_spade.py` e `Flood/` são versões alternativas/antigas; `sistema_spade.py` importa de um `classes.py` que já não existe.
- Bugs conhecidos por corrigir: corrida no arranque (operadores alertam antes de os líderes arrancarem), a barragem pode contar mensagens que não são votos, contrapropostas dos líderes nunca usadas, `json.loads` sem tratamento de erros.
- Nota: o documento original numera os cenários a partir do 2 (não existe "Cenário 1"; presumivelmente seria o cenário base/calmo).

---

# Contexto base do projeto

## Arquitetura Multiagente para um Sistema Descentralizado de Alerta Precoce e Resposta a Inundações Urbanas

### 1. Introdução

Este projeto propõe o desenvolvimento de um sistema multiagente descentralizado para a monitorização, prevenção e resposta a inundações urbanas. O sistema utiliza agentes autónomos que monitorizam diferentes partes do ambiente, tomam decisões com base na informação disponível e comunicam entre si para coordenar ações de prevenção e mitigação de riscos.

A arquitetura contempla uma barragem e três bairros distintos. Cada bairro possui um agente responsável pela monitorização das condições locais e um agente que representa os interesses da respetiva comunidade. Um agente adicional é responsável pela operação da barragem.

Ao contrário de uma arquitetura puramente centralizada, na qual todas as decisões seriam tomadas por uma única entidade, esta abordagem permite que diferentes agentes avaliem o risco segundo as suas próprias observações e objetivos. Os agentes podem apresentar propostas, negociar alternativas e votar em planos de ação conjuntos.

O objetivo principal é demonstrar como a comunicação, a autonomia, a negociação e a tomada de decisão coletiva podem contribuir para uma gestão mais coordenada de situações de risco de inundação.

### 2. Objetivos do sistema

- Monitorizar continuamente as condições hidrológicas e meteorológicas relevantes para a ocorrência de inundações.
- Identificar situações de risco na barragem e nos três bairros.
- Permitir que os agentes tomem decisões autónomas com base nos dados recolhidos e nas suas regras de decisão.
- Facilitar a comunicação entre o operador da barragem, os operadores dos bairros e os líderes comunitários.
- Implementar mecanismos de negociação sobre o caudal e o momento da descarga da barragem, bem como sobre a distribuição de recursos de mitigação.
- Implementar um mecanismo de votação que permita selecionar planos de ação coletivos.
- Garantir que as decisões respeitam restrições operacionais e de segurança.
- Demonstrar uma arquitetura multiagente funcional através de uma simulação implementada em SPADE.

### 3. Arquitetura geral do sistema

O sistema é composto por sete agentes principais, distribuídos por três tipos de funções.

#### 3.1. Agente 1 — Operador da Barragem

Existe um único agente responsável pela monitorização e operação da barragem. Este agente acompanha as condições do reservatório e do sistema hidráulico, avalia os riscos associados às descargas e executa as operações que estejam dentro dos limites de segurança definidos.

#### 3.2. Agentes 2A, 2B e 2C — Operadores dos Bairros

Existe um agente operador para cada bairro. Estes agentes monitorizam as condições locais e avaliam o risco de inundação na respetiva área.

Embora desempenhem a mesma função geral, cada agente possui dados próprios, que podem diferir dos restantes devido à localização, às características do terreno e à capacidade de drenagem de cada bairro.

#### 3.3. Agentes 3A, 3B e 3C — Líderes Comunitários

Cada bairro possui um líder comunitário responsável por representar as necessidades e prioridades da sua população.

Estes agentes recebem informações sobre o risco local, comunicam necessidades ao operador da barragem e participam na negociação e votação de planos de resposta.

Os líderes comunitários representam bairros diferentes e têm o mesmo estatuto no processo de votação. Nenhum dos líderes exerce autoridade hierárquica sobre os restantes.

#### 3.4. Representação esquemática

**Agente 1 — Operador da Barragem**: monitoriza o reservatório, avalia as condições hidráulicas e controla as descargas. Comunica com os três líderes comunitários para partilhar informação e negociar planos de operação.

- **Bairro A**: Agente 2A (Operador do Bairro A); Agente 3A (Líder Comunitário do Bairro A).
- **Bairro B**: Agente 2B (Operador do Bairro B); Agente 3B (Líder Comunitário do Bairro B).
- **Bairro C**: Agente 2C (Operador do Bairro C); Agente 3C (Líder Comunitário do Bairro C).

Os operadores dos bairros monitorizam as condições locais e transmitem os resultados aos respetivos líderes comunitários. Os líderes participam na negociação coletiva com o operador da barragem.

Os sete agentes comunicam através de mensagens, sem dependerem de um agente central responsável por todas as decisões. O operador da barragem mantém, contudo, a responsabilidade técnica pelas operações da infraestrutura.

### 4. Interação dos agentes com o ambiente

O ambiente representa uma região urbana sujeita a precipitação, variações dos níveis de água e possíveis inundações. Inclui uma barragem, um sistema de drenagem e três bairros com características locais distintas.

A interação com o ambiente pode ser implementada através de sensores e atuadores simulados, permitindo testar diferentes cenários sem necessidade de controlar infraestruturas físicas reais.

#### 4.1. Variáveis ambientais

Na barragem e no sistema hidráulico:

- Nível da água no reservatório.
- Previsão e intensidade da precipitação.
- Caudal de entrada e de saída.
- Nível da água no rio a jusante.
- Capacidade disponível e estado do sistema de drenagem.
- Limites operacionais de descarga.

Em cada bairro:

- Nível de água nas ruas ou em pontos de monitorização.
- Profundidade da água no rio ou curso de água próximo.
- Humidade do solo.
- Intensidade da precipitação local.
- Capacidade disponível nos tanques de retenção.
- Disponibilidade de bombas, barreiras e equipas de resposta.
- Nível de risco estimado para a população e para as infraestruturas.

Nem todas as variáveis precisam de corresponder a sensores físicos independentes. Na simulação, poderão ser geradas por um modelo do ambiente ou definidas através de cenários de teste.

#### 4.2. Atuadores

O agente operador da barragem poderá controlar:

- A abertura e o fecho de comportas.
- A alteração do caudal de descarga dentro dos limites permitidos.
- O momento de execução de uma descarga previamente validada.

Os agentes dos bairros poderão representar ações como:

- Ativação de bombas de água.
- Utilização de barreiras temporárias.
- Mobilização de equipas de resposta.
- Ativação de alertas locais.
- Preparação de medidas de proteção ou evacuação, quando aplicável.

Estas ações podem ser modeladas como alterações ao estado do ambiente ou como registos de ações executadas.

### 5. Funções e autonomia dos agentes

#### 5.1. Agente 1 — Operador da Barragem

Responsabilidades:

- Monitorizar o nível do reservatório, a precipitação e as condições do sistema hidráulico.
- Avaliar a necessidade de realizar uma descarga de água.
- Estimar os possíveis efeitos das descargas sobre as zonas a jusante.
- Propor planos de descarga com diferentes caudais e horários.
- Receber propostas e pedidos dos líderes comunitários.
- Participar na negociação de planos conjuntos.
- Verificar a viabilidade técnica das propostas aprovadas.
- Executar as operações de descarga apenas quando estas respeitam os limites de segurança.

Autonomia: o agente decide quando uma intervenção hidráulica é necessária, de acordo com os dados disponíveis e as regras de segurança. A negociação com os restantes agentes não elimina a sua responsabilidade técnica, nem permite que uma votação autorize uma operação insegura.

#### 5.2. Agentes 2A, 2B e 2C — Operadores dos Bairros

Cada operador monitoriza o estado do seu bairro e calcula um indicador de risco local.

Responsabilidades:

- Recolher e atualizar as variáveis ambientais locais.
- Identificar tendências de subida do nível da água.
- Avaliar a capacidade de drenagem e de retenção disponível.
- Estimar o risco de inundação.
- Comunicar alertas e dados relevantes ao respetivo líder comunitário.
- Identificar necessidades de recursos e medidas de mitigação.
- Atualizar as avaliações após alterações no ambiente ou execução de ações.

Autonomia: cada operador avalia o seu bairro de forma independente. Dois bairros podem apresentar níveis de risco diferentes no mesmo instante e, por isso, recomendar ações distintas. Por exemplo, o Bairro A pode apresentar uma subida rápida do nível da água, enquanto o Bairro B ainda dispõe de capacidade de retenção e o Bairro C apresenta apenas risco moderado.

#### 5.3. Agentes 3A, 3B e 3C — Líderes Comunitários

Os líderes comunitários representam os interesses dos respetivos bairros na coordenação das medidas de resposta.

Responsabilidades:

- Receber e interpretar os alertas dos operadores dos bairros.
- Comunicar as necessidades locais ao operador da barragem.
- Solicitar medidas preventivas ou alterações aos planos propostos.
- Avaliar propostas de descarga e de distribuição de recursos.
- Apresentar contrapropostas durante a negociação.
- Participar na votação dos planos coletivos.
- Comunicar as decisões à comunidade e aos agentes envolvidos.

Autonomia: cada líder define as suas preferências com base no risco local, na população potencialmente afetada e nos recursos disponíveis. Um líder pode considerar prioritária a proteção de uma zona residencial vulnerável, enquanto outro pode dar prioridade à prevenção de inundações numa zona com menor capacidade de drenagem.

Os líderes não são subordinados uns dos outros. A decisão coletiva resulta da negociação e do mecanismo de votação estabelecido.

### 6. Modelo de decisão dos agentes

Os agentes utilizam os dados recolhidos, os seus objetivos e um conjunto de regras para escolher as ações mais adequadas.

Na implementação, cada agente poderá atribuir um nível de risco — baixo, moderado, elevado ou crítico — em função de variáveis como o nível da água, a velocidade da sua subida, a precipitação e a capacidade de drenagem disponível.

Exemplos de regras de decisão:

- Se o nível da água subir rapidamente e ultrapassar um limiar definido, o operador do bairro aumenta a avaliação de risco e envia um alerta.
- Se a capacidade dos tanques de retenção for reduzida, o operador do bairro informa o líder comunitário de que existem menos recursos disponíveis para absorver precipitação adicional.
- Se o reservatório atingir um nível elevado, o operador da barragem avalia a necessidade de uma descarga, tendo em conta a previsão meteorológica e as condições a jusante.
- Se um bairro apresentar risco crítico, o respetivo líder solicita prioridade na mobilização de recursos de mitigação.
- Se uma proposta de descarga aumentar o risco num dos bairros, o respetivo líder pode solicitar a alteração do caudal ou do horário.
- Se uma proposta não respeitar os limites operacionais, o operador da barragem rejeita-a ou apresenta uma alternativa tecnicamente viável.

Os limiares e as regras deverão ser definidos na implementação e testados através de cenários simulados.

### 7. Comunicação entre agentes

A comunicação será implementada em SPADE, utilizando mensagens entre agentes identificados por endereços JID.

A estrutura das mensagens deverá permitir identificar o remetente, o destinatário, o tipo de mensagem e o conteúdo transmitido. O conteúdo poderá ser representado em JSON ou num formato estruturado equivalente.

#### 7.1. Comunicação entre operadores e líderes comunitários

Cada operador de bairro comunica com o respetivo líder comunitário. Exemplos:

- O Agente 2A informa o Agente 3A de que o nível da água está a subir rapidamente.
- O Agente 2B comunica ao Agente 3B que os tanques de retenção estão quase cheios.
- O Agente 2C informa o Agente 3C de que o risco local é moderado, mas poderá aumentar se a precipitação se intensificar.

Os líderes utilizam estas informações para definir as suas prioridades e participar na negociação.

#### 7.2. Comunicação com o operador da barragem

O operador da barragem partilha informação sobre o estado do reservatório e apresenta propostas de operação.

Os líderes comunitários podem: solicitar informação adicional; pedir uma alteração ao plano de descarga; comunicar o risco local; propor medidas de mitigação complementares; aceitar ou rejeitar uma proposta.

#### 7.3. Comunicação entre líderes comunitários

Os líderes podem trocar propostas e informação relevante para compreender as prioridades dos outros bairros. Esta comunicação permite identificar conflitos, procurar compromissos e construir uma solução que seja aceitável para a maioria.

#### 7.4. Performativas FIPA-ACL

- INFORM: transmitir dados, alertas ou resultados de uma ação.
- REQUEST: solicitar uma ação ou informação.
- AGREE: indicar que um agente aceita realizar uma ação solicitada.
- REFUSE: recusar um pedido.
- CFP (Call for Proposals): solicitar propostas para um plano ou intervenção.
- PROPOSE: apresentar uma proposta concreta.
- ACCEPT-PROPOSAL: aceitar formalmente uma proposta.
- REJECT-PROPOSAL: rejeitar uma proposta.
- FAILURE: comunicar que uma ação não foi executada com sucesso.

Estas performativas definem o significado das mensagens, mas os procedimentos de negociação, votação e verificação de segurança terão de ser implementados explicitamente na lógica dos agentes.

### 8. Negociação entre agentes

A negociação é um elemento central da arquitetura. O objetivo é permitir que os agentes ajustem os seus planos tendo em conta as necessidades dos diferentes bairros e as limitações do sistema hidráulico.

A negociação incidirá sobre dois temas complementares:

1. A descarga de água da barragem, incluindo o caudal e o momento da operação.
2. A distribuição dos recursos de mitigação disponíveis entre os três bairros.

Estes temas podem ser negociados em conjunto, permitindo avaliar planos completos em vez de tomar decisões isoladas.

#### 8.1. Negociação sobre a descarga da barragem

O operador da barragem apresenta um plano inicial com o caudal pretendido, o horário da descarga e a sua duração estimada. Cada líder comunitário avalia o impacto potencial do plano no seu bairro, com base na informação recebida do respetivo operador.

Os líderes podem propor:

- Uma redução do caudal.
- O adiamento da descarga.
- Uma alteração da duração ou do horário da operação.
- A adoção de medidas locais de mitigação antes da descarga.
- Um plano alternativo que reduza o risco global.

A negociação não consiste em atribuir diretamente uma percentagem da água da barragem a cada bairro. O caudal libertado influencia o sistema hidráulico a jusante, pelo que as propostas devem ser avaliadas de acordo com a dinâmica da água e os limites de segurança.

#### 8.2. Negociação sobre os recursos de mitigação

Os recursos de mitigação são os meios utilizados para reduzir os impactos de uma inundação. Na simulação, poderão incluir: bombas de água; barreiras temporárias ou sacos de areia; capacidade disponível nos tanques de retenção; equipas de resposta e voluntários.

Os recursos poderão ser limitados, criando a necessidade de negociar prioridades. Por exemplo, se existir apenas uma equipa de resposta disponível, os líderes poderão discutir em que bairro deverá ser mobilizada primeiro. A decisão poderá considerar o nível de risco, a velocidade de subida da água, a vulnerabilidade da população e a eficácia esperada da intervenção.

No caso dos tanques de retenção, deve distinguir-se a capacidade de armazenamento disponível da atribuição de um recurso físico. Um tanque localizado num bairro não pode ser tratado como se estivesse automaticamente disponível para outro bairro. A transferência ou partilha só deve ser modelada quando existir uma ligação física plausível.

#### 8.3. Negociação conjunta

1. O operador da barragem avalia o estado do reservatório e apresenta uma proposta inicial de descarga.
2. Os três líderes recebem a proposta e consultam os dados dos respetivos bairros.
3. Cada líder apresenta uma proposta ou um conjunto de condições, identificando as necessidades de mitigação.
4. O operador da barragem avalia as propostas e verifica a sua viabilidade hidráulica.
5. Os agentes procuram uma combinação de caudal, horário e distribuição de recursos que reduza o risco global.
6. É elaborada uma proposta conjunta para votação.
7. Se a proposta for aprovada, o operador da barragem verifica novamente os limites de segurança antes da execução.
8. Se não existir acordo, inicia-se uma nova ronda de negociação ou aplica-se o procedimento alternativo previamente definido.

O objetivo não é garantir que todos os agentes obtenham a sua opção preferida, mas procurar uma solução que concilie os interesses locais e a segurança do sistema.

### 9. Mecanismo de votação

A votação permite selecionar um plano coletivo entre as alternativas negociadas.

Os três líderes comunitários participam na votação, tendo cada bairro direito a um voto. O operador da barragem **não** participa na votação enquanto representante de um bairro, porque tem uma função técnica distinta. Cabe-lhe verificar se a opção aprovada é segura e operacionalmente possível.

#### 9.1. Regra de maioria simples

A decisão é aprovada quando recebe pelo menos dois votos favoráveis em três.

- A: a favor; B: a favor; C: contra — aprovada.
- A: a favor; B: contra; C: contra — rejeitada.
- Os três a favor — aprovada por unanimidade.

Com três votantes, uma maioria simples evita um empate, desde que todos os agentes votem e exista apenas uma proposta submetida a votação. Contudo, pode não haver uma proposta que obtenha dois votos, ou podem existir abstenções ou votos em falta. Por isso, o sistema deverá definir regras para esses casos.

#### 9.2. Votação de várias propostas

Se existirem várias alternativas, o sistema poderá submetê-las a votações sucessivas ou utilizar uma votação por rondas. Uma possibilidade:

1. Os agentes apresentam diferentes planos.
2. O operador da barragem elimina ou reformula os planos que não respeitem as restrições técnicas.
3. Os líderes votam nas alternativas viáveis.
4. Se nenhuma alternativa obtiver dois votos, os agentes negoceiam uma nova proposta.
5. A nova proposta é submetida a votação.

Outra possibilidade é ordenar as propostas por preferência e realizar uma segunda ronda entre as alternativas mais votadas. O método escolhido deve ser explicitado e implementado de forma consistente.

#### 9.3. Casos sem acordo

Se nenhuma proposta obtiver a maioria necessária, o sistema poderá: iniciar uma nova ronda de negociação; solicitar aos líderes que apresentem condições mínimas aceitáveis; reformular a proposta com base nos pontos de concordância; aplicar um procedimento de contingência previamente definido, de acordo com as regras de segurança.

A ausência de consenso não deve levar os agentes a executar automaticamente uma proposta insegura.

#### 9.4. Limites da votação

A votação representa a preferência coletiva dos bairros, mas não substitui as restrições técnicas da infraestrutura. Uma proposta aprovada por dois ou três líderes pode ainda ser rejeitada pelo operador da barragem se ultrapassar os limites operacionais ou criar um risco inaceitável. Nesse caso, o operador comunica a razão da rejeição e propõe uma alternativa viável para nova negociação.

### 10. Distribuição de responsabilidades na decisão final

A decisão final resulta da combinação de três componentes:

- **Avaliação local**: cada operador de bairro identifica o risco e as necessidades da sua área.
- **Decisão coletiva**: os líderes comunitários negoceiam e votam nos planos que consideram mais adequados.
- **Validação técnica**: o operador da barragem confirma que a componente hidráulica do plano aprovado é segura e exequível.

Esta separação permite conciliar a descentralização da tomada de decisão com a responsabilidade técnica pela operação da barragem. A votação não transforma o líder comunitário num operador hidráulico, e o operador da barragem não passa a ser o chefe dos líderes comunitários. Cada agente mantém a sua função específica.

### 11. Exemplo de cenário de negociação

Precipitação intensa está a aumentar o nível da água no reservatório e nos cursos de água da região. O operador da barragem identifica a necessidade de avaliar uma descarga. Ao mesmo tempo:

- O Bairro A apresenta uma subida rápida do nível da água e tem capacidade de drenagem reduzida.
- O Bairro B tem os tanques de retenção quase cheios e necessita de reforçar as medidas de mitigação.
- O Bairro C apresenta risco moderado e dispõe de uma equipa de resposta disponível.

O operador da barragem envia uma proposta inicial de descarga aos três líderes. O líder de A pede que o caudal seja reduzido ou que a operação seja ajustada para limitar o aumento do risco local. O líder de B solicita medidas preventivas adicionais devido à reduzida capacidade de retenção. O líder de C considera possível mobilizar a sua equipa para uma intervenção prioritária, desde que a necessidade nos outros bairros seja avaliada.

Os agentes negoceiam uma alternativa que combina um plano de descarga tecnicamente viável com a mobilização de recursos de mitigação. Os três líderes votam na proposta conjunta. Se obtiver pelo menos dois votos favoráveis, o operador da barragem verifica a segurança da operação e executa a componente hidráulica autorizada. Os agentes dos bairros acompanham as alterações ambientais e comunicam os resultados. Se as condições se alterarem, os agentes poderão iniciar uma nova negociação, demonstrando que a decisão coletiva é dinâmica.

### 12. Implementação em SPADE

O sistema será implementado em Python utilizando a framework SPADE, que permite criar agentes autónomos e estabelecer comunicação assíncrona entre eles através de mensagens XMPP. Cada agente será uma entidade independente, com comportamentos responsáveis pela recolha de informação, análise das condições ambientais, comunicação e tomada de decisão.

#### 12.1. Estrutura dos agentes

Cada agente poderá incluir: um identificador único; variáveis ambientais ou informação recebida; objetivos e regras de decisão; comportamentos periódicos de monitorização; comportamentos de envio e receção de mensagens; lógica de negociação ou votação, quando aplicável; registos das decisões e das ações executadas.

#### 12.2. Comportamentos

- **Monitorização**: atualiza periodicamente os dados do ambiente e identifica alterações relevantes.
- **Avaliação de risco**: calcula o nível de risco com base nos dados disponíveis.
- **Comunicação**: envia alertas, recebe propostas e transmite atualizações.
- **Negociação**: recebe propostas, avalia alternativas e apresenta contrapropostas.
- **Votação**: recolhe e contabiliza os votos dos líderes comunitários.
- **Execução de ações**: aplica as decisões autorizadas ao ambiente simulado e regista os resultados.

A votação e a negociação são funcionalidades da aplicação, não mecanismos que SPADE implemente automaticamente.

#### 12.3. Estrutura das mensagens

Cada mensagem deverá conter, no mínimo: remetente; destinatário; performativa ou tipo de mensagem; identificador da negociação; conteúdo; identificador da proposta, quando aplicável.

O conteúdo poderá incluir o caudal proposto, o horário, os recursos solicitados, o nível de risco e as justificações para aceitar ou rejeitar uma alternativa. O identificador da negociação associa as mensagens ao mesmo processo e evita que propostas de negociações diferentes sejam confundidas.

#### 12.4. Implementação da negociação e da votação

A negociação poderá basear-se no protocolo FIPA Contract Net. O operador da barragem pode iniciar o processo com uma mensagem CFP; os líderes respondem com propostas, que são analisadas e, quando necessário, reformuladas.

A votação é implementada adicionalmente: os três líderes recebem a proposta final, enviam os votos e o sistema calcula se foi atingida a maioria exigida. O resultado é comunicado aos agentes envolvidos. A validação de segurança é realizada pelo operador da barragem antes de qualquer execução hidráulica.

### 13. Simulação do ambiente

O ambiente poderá ser representado por variáveis atualizadas em cada ciclo de simulação: nível do reservatório; caudal de entrada e de saída; intensidade da precipitação; nível de água nos três bairros; capacidade disponível nos tanques de retenção; recursos de mitigação disponíveis; nível de risco de cada bairro.

A execução de uma ação poderá alterar as variáveis do ambiente (por exemplo, uma bomba reduz gradualmente a água acumulada; uma equipa aumenta a capacidade de resposta do bairro). A descarga da barragem deverá influenciar as variáveis hidráulicas segundo as regras do modelo; sem modelo hidrológico detalhado, essas relações podem ser aproximadas por regras de simulação, desde que as limitações sejam documentadas. O ambiente poderá incluir ruído ou variações nas medições para testar a robustez das decisões.

### 14. Cenários de teste e avaliação

(O documento original começa em "Cenário 2"; não há "Cenário 1".)

- **Cenário 2 — Risco elevado num bairro**: um dos bairros apresenta uma subida rápida do nível da água. O operador local comunica o risco e o líder solicita medidas de mitigação.
- **Cenário 3 — Conflito de interesses**: os bairros apresentam necessidades diferentes em relação ao plano de descarga. Os líderes apresentam propostas distintas e negoceiam uma solução.
- **Cenário 4 — Recursos limitados**: existe um número reduzido de bombas, barreiras ou equipas de resposta. Os líderes negoceiam a prioridade de utilização desses recursos.
- **Cenário 5 — Aprovação por maioria**: uma proposta recebe dois votos favoráveis e um contrário. O plano é aprovado coletivamente e segue para validação técnica.
- **Cenário 6 — Ausência de maioria**: nenhuma proposta recebe os votos necessários. O sistema inicia uma nova ronda de negociação ou aplica o procedimento alternativo definido.

A avaliação poderá considerar: o tempo necessário para detetar o risco; o número de mensagens trocadas; o tempo até à decisão coletiva; a utilização dos recursos; o número de propostas rejeitadas por motivos de segurança; a evolução dos níveis de risco.

### 15. Considerações de segurança e limitações

A arquitetura é desenvolvida para fins académicos e de simulação. As regras implementadas não devem ser consideradas suficientes para controlar uma barragem real.

As decisões hidráulicas devem respeitar limites de segurança previamente definidos. O modelo deve também considerar a incerteza das medições e a possibilidade de falhas de comunicação. A votação não pode ultrapassar as restrições físicas do sistema. A distribuição de recursos deve respeitar a sua localização, disponibilidade e capacidade efetiva. Sem um modelo hidrológico realista, as consequências das descargas são aproximações do ambiente simulado e não previsões fiáveis de inundação.

### 16. Conclusão

A arquitetura proposta utiliza sete agentes principais para representar a operação da barragem, a monitorização de três bairros e a representação dos respetivos interesses comunitários. A autonomia dos agentes permite que cada componente avalie as condições relevantes para a sua função; a comunicação por mensagens estruturadas facilita a partilha de informação e a coordenação; a negociação ajusta o caudal e o momento das descargas e a distribuição dos recursos de mitigação; a votação por maioria simples seleciona planos coletivos, enquanto a validação técnica preserva a segurança das operações hidráulicas. A implementação em SPADE permitirá testar estes mecanismos num ambiente simulado e avaliar o impacto da negociação e da decisão coletiva na resposta a situações de risco de inundação.
