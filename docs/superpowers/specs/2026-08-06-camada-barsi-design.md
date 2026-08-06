# Design — Panorama Financeiro · Camada Barsi

- **Data:** 2026-08-06
- **Projeto:** `pbi_panorama_financeiro`
- **Status:** Aprovado (aguardando revisão da spec antes do plano)
- **Autor:** Data Squad (analyst + engineer)

## Contexto e objetivo

O `pbi_panorama_financeiro` é um relatório Power BI (formato PBIP/TMDL) que já
possui dois domínios num mesmo modelo semântico:

1. **Macro Brasil (BCB/SGS)** — Selic, IPCA, Dólar PTAX, PIB.
2. **Ações do Ibovespa** — `d_empresa` (ticker, setor, preço, P/L, faixa 52s) e
   `f_proventos` (dividendos/JCP por tipo), com medidas de DY 12m.

O objetivo é **evoluir o projeto para dar suporte à tomada de decisão de quem segue
o método Barsi** (foco em viver de dividendos de boas pagadoras, dos setores perenes,
compradas abaixo do preço-teto). A camada macro é preservada como **cenário** que
contextualiza a decisão (a Selic/renda fixa baliza o yield-alvo).

### Método Barsi traduzido em BI

- **Setores perenes (BESST):** Bancos, Energia, Saneamento, Seguros, Telecom.
- **Preço-teto (Décio Bazin):** `preço-teto = dividendo médio anual ÷ yield desejado`.
  Preço atual abaixo do teto → sinal de compra.
- **Consistência:** boa pagadora paga todo ano, sem cortes, com dividendo crescente.
- **Bola de neve:** aportes mensais + reinvestimento de dividendos ao longo de décadas
  constroem a "carteira previdenciária".

## Decisões de escopo (confirmadas com o dono)

| Decisão | Escolha |
|---|---|
| Estrutura | **Camada Barsi nova + manter Macro** (macro vira cenário). |
| Universo/dados | **Universo BESST ampliado da B3**, ainda via APIs públicas (brapi + Yahoo). |
| Identidade visual | **Tema padrão do Power BI (sem marca corporativa)** — ver "Conflito de identidade". |
| Yield desejado | **Parametrizável via slicer what-if** (4%–10%, default 6%). |
| Filtro BESST | **Todo o universo, com BESST classificado/destacado** (de-para + override). |
| Histórico de dividendos | **10 anos** (consistência); teto usa média de **5 anos** (Bazin). |
| Recursos | Preço-teto · Consistência · Simulador de renda passiva · Score/Ranking. |
| Arquitetura de cálculo | **A** — estender star schema + pré-agregar em Power Query; lógica em DAX. |

### Conflito de identidade (registrado)

O `CLAUDE.md` deste projeto declara "sem identidade de marca — portfólio público,
decisão do dono; usar tema padrão". Havia uma diretriz organizacional de identidade de marca
corporativa. **O dono optou
explicitamente por manter o tema padrão**, preservando o caráter de portfólio público.
Esta spec registra o conflito e a resolução; um registro de decisão será salvo em
`outputs/decisions/`.

## Arquitetura de cálculo (Abordagem A)

Estender o star schema existente e **pré-agregar no Power Query** o que for pesado em
DAX (grão anual de proventos), mantendo toda a lógica Barsi como medidas DAX. Escolhida
sobre "DAX puro" (streak de anos consecutivos fica complexo/lento) e sobre
"pré-processar em Python" (quebraria a natureza ao-vivo-via-APIs do portfólio).

## Modelo semântico

### Tabelas novas

| Tabela | Tipo | Colunas | Origem |
|---|---|---|---|
| `d_besst` | de-para | `setor_raw`, `besst_sigla` (B/E/S/S/T/—), `besst_nome`, `is_besst` | Tabela inline em M (curada). |
| `f_proventos_anual` | fato agregado | `ticker`, `ano`, `total_proventos` | Reference de `f_proventos`, `Group By(ticker, ano)`. |
| `p_YieldDesejado` | what-if | `valor` (0,04–0,10, passo 0,005) | Parâmetro numérico do Power BI (disconnected). |
| `p_Sim_AporteMensal` | what-if | `valor` (ex.: 100–20.000) | Parâmetro numérico (disconnected). |
| `p_Sim_DYEsperado` | what-if | `valor` (0,03–0,12) | Parâmetro numérico (disconnected). |
| `p_Sim_CrescDividendo` | what-if | `valor` (0,00–0,15) | Parâmetro numérico (disconnected). |
| `p_Sim_Anos` | what-if | `valor` (1–30) | Parâmetro numérico (disconnected). |

### Tabelas alteradas

- **`d_empresa`** — nova coluna resolvida **`besst`**: no partition M, após montar as
  cotações, fazer merge com `d_besst` por `setor` e aplicar **override por ticker** para
  o caso ambíguo (brapi agrupa "Finanças e Seguros" → precisa separar banco × seguradora).
  Universo ampliado: o parâmetro passa a se chamar **`UniversoTickers`** e inclui boas
  pagadoras BESST fora do Ibovespa (ex.: TAEE11, EGIE3, CPLE6, SAPR11, CSMG3, BBSE3,
  PSSA3, ITSA4, BBAS3, além das já presentes). Atualização manual documentada.
- **`f_proventos`** — histórico estendido para **10 anos** via ajuste em `fnYahooProventos`.

### Relacionamentos novos

- `f_proventos_anual[ticker]` * → 1 `d_empresa[ticker]`.
- `f_proventos[data_pagamento]` * → 1 `d_calendario[data]` (série de proventos por ano
  no Detalhe da Ação). Cross-filter single; não afeta medidas macro (páginas separadas).

> `d_calendario` continua sendo a única tabela de datas (auto date/time desligado) e
> deve cobrir ≥10 anos de histórico; marcar como Tabela de Data no Desktop.

## Medidas DAX (nova pasta `08. Barsi`)

### Preço-teto (Bazin)
- `Dividendo Médio Anual (5a)` — média dos `total_proventos` dos **últimos 5 anos
  completos** em `f_proventos_anual`.
- `Yield Desejado` = `SELECTEDVALUE(p_YieldDesejado[valor], 0.06)`.
- `Preço-Teto` = `DIVIDE([Dividendo Médio Anual (5a)], [Yield Desejado])`.
- `Margem vs Teto %` = `DIVIDE([Preço-Teto] - [Preço Atual Ação], [Preço Atual Ação])`
  (positivo = abaixo do teto = comprar).
- `Sinal Barsi` = `IF([Preço Atual Ação] <= [Preço-Teto], "Comprar", "Aguardar")`.
- `DY Médio 5a` = `DIVIDE([Dividendo Médio Anual (5a)], [Preço Atual Ação])`.

### Consistência (10 anos)
- `Anos Pagando (10a)` — contagem de anos com `total_proventos > 0` nos últimos 10 anos.
- `Anos Consecutivos` — maior sequência de anos pagando terminando no último ano completo.
- `Cortes de Dividendo (10a)` — nº de anos em que o total anual caiu vs o ano anterior.
- `Crescimento Dividendo CAGR 5a` — `(div_ano_final / div_ano_inicial)^(1/n) - 1`.

### Score Barsi (0–100, pesos fixos e documentados)
Soma ponderada de componentes normalizados (0–1). Pesos iniciais propostos:

| Componente | Peso | Racional |
|---|---|---|
| DY Médio 5a (normalizado, teto em 12%) | 30% | Núcleo do método: renda. |
| Anos Consecutivos (normalizado, teto 10) | 25% | Consistência/previsibilidade. |
| is-BESST (1/0) | 15% | Setor perene. |
| Margem vs Teto % (>0 pontua, teto em +30%) | 20% | Comprar barato. |
| Faixa de P/L (0–20 pontua melhor; penaliza P/L≤0) | 10% | Sanidade de preço. |

Pesos **não parametrizáveis** nesta versão (YAGNI); documentados para revisão futura.

### Simulador de renda passiva (bola de neve)
Medidas sobre parâmetros `p_Sim_*` (juros compostos com reinvestimento de dividendos e
crescimento anual do dividendo):
- `Patrimônio Projetado` — FV de aportes mensais + reinvestimento ao longo de `Anos`.
- `Renda Passiva Mensal Projetada` — `Patrimônio Projetado × DYEsperado / 12` no horizonte.
- `Total Aportado` e `Dividendos Reinvestidos` — decomposição do patrimônio final.

Fórmula base documentada no plano; usa uma tabela auxiliar de anos (1..`Anos`) como eixo.

### Medidas mantidas
`DY 12m`, `Proventos 12m`, `Preço Atual Ação`, `P/L`, `Posição 52 Semanas`,
indicadores macro dedicados e pasta `06. Diagnóstico`.

## Relatório — páginas

Tema padrão do Power BI (sem paleta/fonte/logo corporativa).

1. **Cenário Macro** *(existente — ajuste leve)*: Selic/IPCA/Dólar como contexto do
   yield-alvo ("renda fixa em X% → exigir yield acima disso").
2. **Explorar Macro** *(existente — mantém)*.
3. **Seleção Barsi / Screener** *(upgrade da atual p3 Dividendos)*: tabela do universo —
   Ticker · Empresa · BESST · Preço · **Preço-Teto** · **Margem vs Teto %** · **Sinal**
   (formatação condicional) · DY 12m · DY 5a · Anos consec. · P/L · **Score**. Slicers:
   BESST, Sinal, **Yield Desejado (what-if)**, busca por ticker. Card "N ações abaixo do teto".
4. **Detalhe da Ação** *(nova — drill-through a partir da p3)*: barras de proventos por
   ano (10a) + linha de DY; preço vs teto; faixa 52 semanas; painel de consistência; P/L.
5. **Ranking Barsi** *(nova)*: Top N por Score com breakdown dos componentes.
6. **Simulador de Renda Passiva** *(nova)*: sliders (aporte, DY, crescimento, anos) +
   área/linha de patrimônio e renda mensal ao longo do tempo + cards de resultado
   (patrimônio final, renda mensal no horizonte, total aportado × dividendos reinvestidos).

Página/painel de **Diagnóstico** mantido (medidas da pasta `06. Diagnóstico`),
exposto como tooltip ou página oculta.

## Power Query / M

- `fnYahooProventos` — janela de **10 anos** (`range=10y` ou `period1 = hoje-10a`).
- `d_besst` — tabela inline curada (setor→BESST) + lista de override por ticker.
- Coluna `besst` resolvida dentro do partition M de `d_empresa` (merge + override).
- `f_proventos_anual` — reference de `f_proventos`, `Group By(ticker, Year)`.
- `UniversoTickers` — parâmetro ampliado; atualização manual a cada rebalanceamento/revisão.

## DQ, documentação e decisões

- **Contratos** (`contracts/panorama/`): incluir `besst`, sanity de `preço-teto` (>0 quando
  há dividendo), janela de 10 anos em `f_proventos`.
- **`scripts/dq_check_panorama.py`**: cobrir as novas colunas/tabelas.
- **`README.md`** e **`CLAUDE.md`** do projeto: novas tabelas, páginas, universo, gotchas.
- **`outputs/decisions/`**: (a) ambiguidade de setor da brapi → override por ticker;
  (b) teto sobre média de 5 anos (Bazin) × consistência em 10 anos; (c) conflito de
  identidade resolvido (tema padrão por decisão do dono).

## Limitações assumidas

- **Setor da brapi é grosseiro** ("Finanças e Seguros" mistura banco e seguradora) →
  override manual por ticker na resolução do `besst`.
- **Cobertura Yahoo parcial** — alguns tickers sem histórico de dividendos; sinalizado
  no diagnóstico (medida de tickers com proventos).
- **Score com pesos fixos** — não parametrizável nesta versão (YAGNI).
- **Refresh mais lento** — 10 anos de proventos = 1 chamada Yahoo por ticker; universo
  ampliado aumenta o tempo de atualização (aceito).

## Fora de escopo (YAGNI)

- Integração com carteira real (Fabric/posições) — descartado nesta fase.
- Marca/tema corporativo — descartado por decisão do dono.
- Pesos de Score configuráveis por slicer — descartado.
- Alertas/refresh automatizado — descartado.

## Critérios de sucesso

1. O universo BESST ampliado carrega com `besst` corretamente classificado (incluindo
   overrides banco×seguradora) e cobertura de preço/proventos reportada no diagnóstico.
2. A página Screener lista, para cada ticker, preço-teto, margem, sinal e score,
   reagindo ao slicer de yield desejado.
3. O Detalhe da Ação mostra 10 anos de proventos e as métricas de consistência.
4. O Simulador projeta patrimônio e renda passiva coerentes com os parâmetros.
5. Contratos DQ, README e CLAUDE.md atualizados; registros de decisão salvos.
