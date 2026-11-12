# Arquitetura Multiagente para um Sistema Descentralizado de Alerta Precoce e Resposta a Inundações Urbanas

## 1. Introdução e objetivos

Este projeto propõe o desenvolvimento de um sistema multiagente descentralizado para monitoramento, prevenção e resposta a inundações urbanas. O sistema utiliza agentes autônomos que monitoram diferentes partes do ambiente, tomam decisões com base nas informações disponíveis e se comunicam para coordenar ações de prevenção e mitigação de riscos.

A arquitetura contempla uma barragem e três bairros. Cada bairro possui um agente responsável pelo monitoramento das condições locais e outro que representa os interesses da comunidade. Dois agentes adicionais são responsáveis pela operação da barragem e pelo diretório de serviços.

A arquitetura foi analisada e desenhada com a metodologia Gaia (Zambonelli, Jennings e Wooldridge, 2003), que descreve um sistema multiagente como uma organização de papéis que interagem segundo regras.

Os principais objetivos são:

- Monitorar as condições hidrológicas e meteorológicas.
- Identificar situações de risco na barragem e nos bairros.
- Permitir decisões autônomas com base em regras próprias.
- Negociar planos de descarga e contratação de recursos entre bairros.
- Implementar votação para decisões coletivas.
- Garantir que as operações respeitem restrições técnicas e de segurança.
- Demonstrar o funcionamento da arquitetura por meio de uma simulação em SPADE.

## 2. Arquitetura e agentes (metodologia Gaia)

O sistema é composto por oito agentes:

| Agentes | Função | Papéis Gaia |
|---|---|---|
| Agente 1 — Operador da Barragem | Monitora o reservatório, propõe planos de descarga, verifica sua segurança e executa as operações autorizadas. | OperadorBarragem, CoordenadorVotacao |
| Agentes 2A, 2B e 2C — Operadores dos Bairros | Monitoram as condições locais, avaliam o risco, controlam o estoque de recursos e executam serviços contratados. | MonitorBairro, ExecutorLocal |
| Agentes 3A, 3B e 3C — Líderes Comunitários | Representam os bairros, participam da negociação e votação, gerenciam a moeda e contratam ou oferecem serviços. | RepresentanteBairro, Comprador, Fornecedor |
| Agente 4 — Diretório de Serviços | Registra os serviços disponíveis, seus preços e fornecedores, respondendo às consultas dos líderes. | Diretorio |

Na metodologia Gaia, um papel é um conjunto de responsabilidades, e um agente pode desempenhar mais de um papel. O operador da barragem desempenha dois papéis porque a votação é implementada separadamente da negociação (seção 6). O líder desempenha três porque o mesmo bairro representa a comunidade nas decisões coletivas e pode comprar ou vender recursos em momentos diferentes.

Os agentes possuem responsabilidades distintas e se comunicam sem depender de uma entidade central responsável por todas as decisões. O diretório apenas armazena e fornece informações, enquanto o operador da barragem mantém a responsabilidade técnica pelas operações hidráulicas.

### 2.1. Estrutura organizacional

A Figura 1 mostra a estrutura organizacional do sistema. Os três líderes são pares, com o mesmo estatuto, e nenhum manda nos outros. O operador da barragem tem autoridade técnica sobre as comportas, mas não manda nos líderes, porque uma descarga normal depende da votação. Dentro de cada bairro, o líder decide e o operador executa, podendo recusar um pedido quando o estoque não chega. O diretório é um serviço passivo, consultado por todos os líderes.

[INSERIR AQUI A IMAGEM gaia_estrutura.png]

*Figura 1. Estrutura organizacional. As setas contínuas indicam troca de mensagens. As setas tracejadas indicam o efeito físico de uma descarga, que chega aos bairros pelo rio e pela drenagem. O Contract Net pode ligar quaisquer dois líderes.*

## 3. Ambiente e modelo de decisão

O ambiente representa uma região urbana composta por uma barragem, um sistema de drenagem e três bairros com características distintas. Sua evolução será simulada por meio de variáveis ambientais e ações dos agentes.

Variáveis principais:

- Nível da água no reservatório e nos bairros.
- Precipitação e caudais de entrada e saída.
- Nível da água a jusante.
- Capacidade de drenagem.
- Humidade do solo.
- Disponibilidade de bombas, barreiras e equipes de resposta.
- Estoque de recursos e moeda de cada bairro.

O operador da barragem poderá controlar comportas e caudais de descarga. Os operadores dos bairros poderão ativar bombas, utilizar barreiras, mobilizar equipes e emitir alertas.

Cada operador de bairro avalia autonomamente o risco local, classificando-o como baixo, moderado, elevado ou crítico, de acordo com variáveis como nível da água, velocidade de subida, precipitação e capacidade de drenagem.

Exemplos de regras:

- Uma subida rápida do nível da água pode gerar um alerta ao líder comunitário.
- A redução da capacidade de drenagem aumenta a avaliação de risco.
- Um bairro com risco elevado e falta de recursos pode solicitar serviços a outro bairro.
- Um bairro só oferece recursos quando mantém uma reserva mínima e apresenta condições adequadas para isso.

Os líderes definem suas prioridades com base no risco local, na população potencialmente afetada e nos recursos disponíveis.

## 4. Comunicação entre agentes

A comunicação será implementada em SPADE, utilizando mensagens assíncronas entre agentes identificados por endereços JID. O conteúdo poderá ser estruturado em JSON.

As principais interações são:

- Operadores e líderes: transmissão de alertas, avaliações de risco, necessidades e disponibilidade de recursos.
- Operador da barragem e líderes: compartilhamento de informações e troca de propostas sobre as descargas.
- Entre líderes: negociação de planos coletivos e contratação de serviços.
- Líderes e diretório: publicação, atualização, remoção e consulta de ofertas.

Estas interações formam o modelo de interações do Gaia, e os protocolos de negociação, votação e contratação estão descritos na seção 5.

As mensagens utilizarão performativas inspiradas em FIPA-ACL:

| Performativa | Finalidade |
|---|---|
| INFORM | Transmitir informações, alertas e resultados. |
| REQUEST | Solicitar uma ação ou informação. |
| AGREE / REFUSE | Aceitar ou recusar uma solicitação. |
| CFP | Solicitar propostas de serviços. |
| PROPOSE | Apresentar uma proposta. |
| ACCEPT-PROPOSAL / REJECT-PROPOSAL | Aceitar ou rejeitar uma proposta. |
| FAILURE | Informar falha na execução de uma ação. |

As performativas definem o significado das mensagens; os mecanismos de negociação e votação serão implementados na lógica dos agentes.

## 5. Negociação e votação

O sistema possui dois processos de negociação distintos: a negociação coletiva das descargas da barragem e a contratação bilateral de serviços entre bairros.

### 5.1. Negociação da descarga da barragem

O operador da barragem apresenta uma proposta inicial indicando o caudal, o horário e a duração estimada da descarga.

Os três líderes avaliam os possíveis impactos em seus bairros e podem aceitar, rejeitar ou apresentar alternativas, como reduzir o caudal, adiar a operação ou adotar medidas locais de mitigação.

O operador analisa as respostas e pode apresentar uma nova proposta, iniciando outra rodada de negociação. Quando existir uma proposta final, ela será submetida à votação.

A negociação termina quando uma proposta é aprovada ou quando é atingido o limite de rodadas definido. Caso não haja acordo, será aplicado o procedimento de contingência estabelecido.

### 5.2. Votação

Os três líderes comunitários participam da votação, cada um representando um bairro e tendo direito a um voto. O operador da barragem não vota.

Uma proposta é aprovada por maioria simples, ou seja, com pelo menos dois votos favoráveis em três. O operador da barragem coleta e contabiliza os votos.

Após a aprovação, o operador verifica se a operação é tecnicamente viável e respeita os limites de segurança. A votação nunca pode autorizar uma operação insegura.

Se não houver acordo a tempo ou se a situação exigir uma resposta imediata, o operador poderá executar um procedimento de contingência previamente definido, respeitando os limites técnicos e informando os líderes.

No modelo Gaia, a maioria de dois votos em três, a validação técnica depois da votação e o procedimento de contingência são regras organizacionais. Valem para o sistema inteiro, e nenhum agente pode ignorá-las.

### 5.3. Contratação de serviços entre bairros

Os recursos disponíveis poderão incluir bombas, sacos de areia, barreiras temporárias e equipes de resposta.

Cada líder publica no diretório os recursos que seu bairro pode oferecer e os respectivos preços. Quando precisar de um recurso, consulta o diretório e solicita propostas aos fornecedores.

A contratação utiliza o protocolo FIPA Contract Net:

1. O comprador envia um CFP aos fornecedores.
2. Os fornecedores apresentam propostas com preço e quantidade.
3. O comprador pode aceitar, rejeitar ou apresentar uma contraproposta.
4. Após a aceitação, o recurso é reservado.
5. O operador do bairro fornecedor executa o serviço e comunica o resultado.
6. O pagamento ocorre somente após a confirmação da execução. Em caso de falha, a reserva é liberada e não há pagamento.

O operador do bairro controla o estoque físico, enquanto o líder gerencia a moeda e toma as decisões comerciais. O diretório mantém as informações sobre as ofertas e a disponibilidade.

A reserva mínima exigida para oferecer recursos (seção 3) e o pagamento só após a confirmação da execução são as regras organizacionais da contratação entre bairros.

Preços iniciais fictícios:

| Serviço | Preço base |
|---|---|
| Sacos de areia (por lote) | 10 |
| Bomba de água | 20 |
| Equipe de resposta | 30 |

Na negociação, o comprador começa oferecendo cerca de 60% do preço base. O vendedor aceita valores iguais ou superiores a 70% do preço base; caso contrário, pode apresentar uma contraproposta. O número máximo de rodadas será definido na implementação.

## 6. Implementação em SPADE

O sistema será desenvolvido em Python utilizando a framework SPADE, que permite criar agentes autônomos e estabelecer comunicação assíncrona por meio de mensagens XMPP.

Cada agente terá comportamentos específicos, que poderão incluir:

- Monitoramento: atualização periódica das variáveis ambientais.
- Avaliação de risco: classificação do risco local.
- Comunicação: envio e recebimento de mensagens.
- Negociação: troca de propostas e contrapropostas.
- Votação: coleta e contabilização dos votos dos líderes.
- Gestão de serviços: publicação e consulta de ofertas.
- Execução: aplicação das ações autorizadas no ambiente simulado.

A negociação da descarga será implementada por um mecanismo simples de troca de propostas e contrapropostas entre o operador da barragem e os líderes comunitários, podendo ocorrer em várias rodadas.

A votação será implementada separadamente: o operador envia a proposta final aos três líderes, coleta seus votos e verifica se a maioria necessária foi alcançada.

A contratação de serviços utilizará o protocolo FIPA Contract Net, iniciado pelo líder que necessita do recurso.

As mensagens deverão conter remetente, destinatário, tipo de mensagem, identificador da negociação e conteúdo. Quando aplicável, incluirão também o identificador da proposta, o caudal, o horário, o serviço, a quantidade e o preço.

A validação técnica das descargas será sempre realizada pelo operador da barragem antes da execução.

## 7. Simulação e avaliação

O ambiente será atualizado a cada ciclo de simulação, considerando os níveis de água, precipitação, caudais, capacidade de drenagem, riscos locais e recursos disponíveis.

As ações dos agentes modificarão o estado do ambiente. Por exemplo, a ativação de uma bomba poderá reduzir o nível de água acumulada, enquanto a mobilização de uma equipe poderá aumentar a capacidade de resposta de um bairro.

A descarga da barragem também influenciará as variáveis hidráulicas segundo as regras definidas para o modelo. Caso não exista um modelo hidrológico detalhado, essas relações serão aproximadas e suas limitações deverão ser documentadas.

Serão avaliados três cenários:

1. Risco elevado em um bairro: um operador identifica uma subida rápida da água e o líder solicita medidas de mitigação.
2. Conflito de interesses: os bairros apresentam necessidades diferentes em relação à descarga, exigindo negociação e votação.
3. Recursos limitados: um bairro precisa de um recurso indisponível localmente e negocia sua contratação com outro bairro.

A avaliação poderá considerar o tempo de detecção do risco, o número de mensagens trocadas, o tempo até a decisão coletiva, a utilização dos recursos, a evolução do risco, as propostas rejeitadas por segurança, o número de transações e os preços negociados.

## 8. Segurança e limitações

A arquitetura destina-se exclusivamente a fins acadêmicos e de simulação. Não deve ser considerada adequada para controlar uma barragem real.

As operações hidráulicas devem respeitar limites de segurança previamente definidos, independentemente do resultado da votação. O modelo deverá considerar a incerteza das medições e possíveis falhas de comunicação.

A distribuição de recursos deve respeitar sua disponibilidade e capacidade efetiva. Caso não exista um modelo hidrológico realista, as consequências das descargas serão aproximações do ambiente simulado, e não previsões confiáveis de inundação.

A moeda e os preços utilizados são fictícios e não representam custos reais.

## Referências

Zambonelli, F., Jennings, N. R., & Wooldridge, M. (2003). Developing multiagent systems: The Gaia methodology. ACM Transactions on Software Engineering and Methodology, 12(3), 317–370.
