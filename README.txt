AI_FloodAgents
Sistema multiagente descentralizado de alerta precoce e resposta a inundações
urbanas, em Python com SPADE.
Sistemas Autónomos e Inteligentes (ISIA), 2026/27.

Grupo:
  Telma Freitas, up202301622
  Ana Sofia Quintero, up202300906
  Yunnie Zita, up202309709


1. O QUE É

Uma barragem e três bairros (A, B e C) simulados, com oito agentes que
comunicam por mensagens FIPA-ACL sobre XMPP, sem nenhuma entidade central:

  - Operador da barragem (1): monitora o reservatório, propõe descargas,
    valida a segurança e executa. Não vota.
  - Operadores dos bairros (3): medem o nível de água, avaliam o risco e
    controlam o estoque de recursos (bombas, barreiras, equipes).
  - Líderes comunitários (3, agentes BDI): representam o bairro, negociam e
    votam as descargas e contratam recursos a outros bairros.
  - Diretório de serviços (1): guarda as ofertas de recursos dos bairros.

O sistema mostra a negociação da descarga em várias rodadas, a votação por
maioria (2 votos em 3), a contingência da barragem e a contratação de
recursos entre bairros com o protocolo FIPA Contract Net.


2. REQUISITOS

  - Python 3.10 a 3.14 (testado com 3.13.2), em Windows, Linux ou macOS.
  - Internet apenas para instalar as bibliotecas.
  - Não é preciso instalar nenhum servidor XMPP: o SPADE arranca um servidor
    embutido em cada execução.


3. INSTALAÇÃO

Na pasta deste ficheiro, com um ambiente virtual novo.

Windows (PowerShell):

    python -m venv .venv
    .\.venv\Scripts\Activate
    python -m pip install -r requirements.txt
    python -m pip uninstall winloop

  Se aparecer "running scripts is disabled on this system", antes de ativar:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

  O passo do winloop é necessário: no Windows ele é instalado como
  dependência e causa erros assíncronos no SPADE.

Linux ou macOS:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt

O requirements.txt tem as versões exatas de todas as bibliotecas.


4. COMO CORRER

Com o ambiente ativo, na pasta do projeto:

    python main.py                       cenário por omissão (risco_elevado)
    python main.py conflito
    python main.py recursos_limitados
    python main.py conflito -v           mostra também cada mensagem e
                                         cada ciclo do ambiente

Cenários (os três primeiros são os da especificação):

  risco_elevado       um bairro com subida rápida da água; o líder pede
                      mitigação.
  conflito            os bairros divergem sobre a descarga: negociação,
                      votação e descarga da barragem.
  recursos_limitados  um bairro sem bombas contrata-as a outro bairro
                      (Contract Net).
  calmo, cheia        estados de teste, sem história própria.

Cada execução demora cerca de um minuto e meio: uns 25 segundos a arrancar os
agentes e 50 segundos de simulação. Não corra duas ao mesmo tempo (usam a
mesma porta local).

O que aparece no terminal: eventos com o tempo, como ALERTA, MITIGAÇÃO,
OFERTA, VOTAÇÃO, DESCARGA, CONTINGÊNCIA, CONTRATO, SERVIÇO e PAGAMENTO. No fim
mostra o estado final e as métricas, e grava-as em resultados/<cenário>/
(ciclos.csv, eventos.csv e resumo.json).


5. OUTROS COMANDOS

    python -m unittest discover -s tests       testes automáticos (135)

    python gerar_docs.py                       documentação do código em HTML
                                               (docs/html/index.html), a partir
                                               das docstrings, com o pdoc

    python graficos.py                         gráficos dos cenários em
                                               resultados/<cenário>/ (PNG);
                                               corra antes os cenários.
                                               Usa o matplotlib, que o
                                               requirements.txt já instala

    python experimentos.py --lista             mostra os experimentos
    python experimentos.py base mitigacao      corre estes grupos e junta o
                                               resultado em
                                               resultados/experimentos/
                                               comparacao.csv

Os experimentos correm o mesmo cenário mudando um parâmetro de cada vez
(por exemplo, a mitigação sem efeito) e comparam as métricas.


6. ESTRUTURA

  main.py            ponto de entrada: cria o ambiente e os agentes e corre
  config.py          constantes (limites, preços, tempos)
  ambiente.py        o mundo simulado: reservatório, chuva, bairros
  risco.py           classificação do risco de cada bairro
  cenarios.py        os cenários (estado inicial e chuva)
  mensagens.py       criar e ler as mensagens FIPA-ACL
  rede.py            quem pode falar com quem
  mercado.py         regras de preços e de reserva mínima
  metricas.py        recolha das métricas de avaliação
  graficos.py        gráficos dos resultados
  experimentos.py    experimentos comparativos
  gerar_docs.py      gera a documentação HTML (docs/html) com o pdoc
  registo.py         saída do terminal
  agentes/           barragem.py, operador.py, lider.py (com lider.asl, a parte
                     BDI em AgentSpeak), diretorio.py e contract_net.py
  tests/             testes automáticos
  docs/              documentação do código (HTML gerado das docstrings, em
                     docs/html/index.html) e notas de desenho


7. NOTAS

  - A moeda e os preços são fictícios, e o modelo da água é uma aproximação
    simples. O sistema é só uma simulação académica e não serve para
    controlar uma barragem real.
  - O servidor XMPP embutido cria ficheiros server.db* na pasta. Podem ser
    apagados.
