// Líder comunitário (agentes 3A, 3B, 3C): a parte BDI.
//
// Crenças:    o risco do bairro (vem do operador), a proposta de descarga em
//             análise (vem da barragem) e o que o bairro aguenta.
// Desejos:    proteger o bairro e, quando o risco sobe, mitigá-lo.
// Intenções:  pedir recursos ao operador; aceitar, contrapropor ou rejeitar
//             uma descarga.
//
// As ações com ponto inicial (.registar, .pedir_mitigacao, .responder) estão
// em agentes/lider.py. As mensagens e o envio ficam no Python; aqui só se decide.
// Os átomos não levam acentos: "critico" em vez de "crítico".

// --- Crenças iniciais ---------------------------------------------------

risco(baixo).

// caudal máximo que o bairro aceita, por risco (espelha CAUDAL_ACEITE em config.py)
caudal_aceite(baixo, 80).
caudal_aceite(moderado, 50).
caudal_aceite(elevado, 25).
caudal_aceite(critico, 0).

// recursos a pedir por risco (espelha RECURSOS_POR_RISCO em config.py)
recurso(moderado, bombas, 1).
recurso(elevado, bombas, 2).
recurso(elevado, barreiras, 1).
recurso(critico, bombas, 3).
recurso(critico, barreiras, 2).
recurso(critico, equipas, 1).

// --- Desejo inicial -----------------------------------------------------

!proteger_bairro.

+!proteger_bairro <-
    .registar("desejo adotado: proteger o bairro").

// --- Risco: crença -> desejo -> intenção --------------------------------

+risco(baixo) <-
    .registar("risco baixo: nada a pedir").

+risco(R) : R \== baixo <-
    !mitigar(R).

+!mitigar(R) <-
    .findall(par(T, N), recurso(R, T, N), Pedido);
    .pedir_mitigacao(Pedido).

// --- Proposta de descarga: aceitar, contrapropor ou rejeitar ------------
// Cabe no que o risco do bairro permite? Aceita.
// Não cabe mas o bairro aguenta alguma descarga? Contrapropõe o seu limite.
// O bairro não aguenta nenhuma descarga? Rejeita.

+proposta(Id, Caudal) : risco(R) & caudal_aceite(R, Limite) & Caudal <= Limite <-
    .responder(Id, aceita, Caudal).

+proposta(Id, Caudal) : risco(R) & caudal_aceite(R, Limite) & Caudal > Limite & Limite > 0 <-
    .responder(Id, contraproposta, Limite).

+proposta(Id, Caudal) : risco(R) & caudal_aceite(R, Limite) & Caudal > Limite & Limite == 0 <-
    .responder(Id, rejeita, 0).

// --- Votação da proposta final: só sim ou não ----------------------------
// Na votação não se negoceia, por isso não há contraproposta. Vota sim se o
// caudal cabe no que o risco do bairro permite, e não se não cabe.

+votacao(Id, Caudal) : risco(R) & caudal_aceite(R, Limite) & Caudal <= Limite <-
    .votar(Id, sim).

+votacao(Id, Caudal) : risco(R) & caudal_aceite(R, Limite) & Caudal > Limite <-
    .votar(Id, nao).
