# Dividendos Ibovespa — Página de Dividend Yield (Top 15)

**Data:** 2026-07-30
**Autor:** Fabiano Amaral
**Status:** Spec aprovado — pronto para plano de implementação

## 1. Objetivo

Adicionar ao projeto `pbi_panorama_macro_bcb` uma página de relatório que lista as
**15 empresas do Ibovespa com maior Dividend Yield dos últimos 12 meses** e o
**setor** de cada uma. Estende o painel macro (BCB/SGS) com um novo domínio de
**renda variável (ações B3)**, alimentado por uma segunda API pública (**brapi.dev**).

## 2. Decisões de escopo (brainstorming)

| Decisão | Escolha | Trade-off aceito |
|---|---|---|
| Onde vive o domínio de ações | **Nova página no projeto macro** (mesmo SemanticModel) | Dois domínios (macro + bolsa) coexistem no mesmo modelo, sem relacionamento entre eles — menor coesão em troca de um único artefato. |
| Universo do ranking | **Ibovespa (~85 ações)** | Lista precisa ser semeada estaticamente (o brapi não expõe a composição do índice); requer atualização trimestral manual. |
| Definição de DY 12m | **Proventos (div + JCP) pagos nos últimos 12m ÷ preço atual** | Padrão de mercado (StatusInvest/Fundamentus). |
| Módulo de setor | **Endpoint `list` (free)** | Evita o módulo pago `summaryProfile`. |

## 3. Fonte de dados — brapi.dev

API pública de ações da B3. **Requer token** (cadastro gratuito no dashboard).

- **Setor + nome + preço atual:** `GET /api/quote/list?token=…`
  - Resposta inclui, por ativo: `stock` (ticker), `name`, `sector`, `close` (preço).
  - Campo `availableSectors` lista os setores disponíveis.
  - Filtrado por *inner join* com a lista-semente do Ibovespa.
- **Proventos:** `GET /api/quote/{ticker}?range=1y&dividends=true&token=…`
  - Retorna `dividendsData.cashDividends[]` com `paymentDate`, `rate`, `label`/`relatedTo`
    e tipo (dividendo / JCP).
  - Uma chamada por ticker (~85 no total).

**Restrições:** plano free tem *rate limit* (HTTP 429). A lista de ~85 tickers cabe no
free; se necessário, serializar as chamadas de proventos.

### Token em repositório público

Este projeto é um portfólio público no GitHub. O token **não** pode ser versionado.

- Parâmetro M `BrapiToken` (Text, **default `""`**). O usuário preenche localmente no
  Power BI Desktop antes do refresh.
- `expressions.tmdl` é commitado com o default vazio.
- README documenta o passo de preencher o token.
- O hook `detect-secrets` (PreToolUse/Bash) barra commit caso um token real seja staged.

### Lista-semente do Ibovespa

- Parâmetro M `IbovTickers` (Text) com a composição atual do Ibovespa (tickers separados
  por vírgula), obtida no site da B3.
- Comentário no parâmetro indicando a data da carteira e o lembrete de atualização
  trimestral (rebalanceamento da B3).

## 4. Modelagem — adições ao SemanticModel

Reaproveita `d_calendario`. Duas tabelas novas, sem relação com o domínio macro.

```
d_empresa (ticker, nome, setor, preco_atual)
      │ 1
      │ *
f_proventos (ticker, data_pagamento, valor, tipo)
      │ *
      │ 1
d_calendario (data, …)      ← reusa o calendário existente
```

**Tabelas:**

- `d_empresa` — uma linha por ticker do Ibovespa.
  - `ticker` (text, PK), `nome` (text), `setor` (text), `preco_atual` (decimal —
    snapshot do preço no momento do refresh).
- `f_proventos` — uma linha por provento pago no último ano.
  - `ticker` (text), `data_pagamento` (date), `valor` (decimal), `tipo` (text: `Dividendo`|`JCP`).

**Relacionamentos:**

- `f_proventos[ticker]` → `d_empresa[ticker]` (muitos-para-um, filtro único).
- `f_proventos[data_pagamento]` → `d_calendario[data]` (muitos-para-um, filtro único).

## 5. Camada M (`expressions.tmdl` / novas partições)

- Novos parâmetros: `BrapiToken` (default `""`), `IbovTickers` (composição atual),
  `UrlBaseBrapi` (default `"https://brapi.dev"`).
- Função `fnBrapiProventos(ticker as text) as table` — chama
  `Web.Contents(UrlBaseBrapi, [RelativePath="api/quote/" & ticker,
  Query=[range="1y", dividends="true", token=BrapiToken]])` (padrão gateway-safe:
  RelativePath/Query separados), extrai `cashDividends`, tipa `paymentDate` como date e
  `rate` como number, deriva `tipo`.
- `d_empresa` — chama `/api/quote/list`, expande a lista de ativos, seleciona
  `stock`/`name`/`sector`/`close`, faz *inner join* com `IbovTickers` (split por vírgula),
  renomeia para `ticker`/`nome`/`setor`/`preco_atual`.
- `f_proventos` — percorre `IbovTickers`, chama `fnBrapiProventos` por ticker, empilha
  (`Table.Combine`).

## 6. Medidas DAX (novas, em `_Medidas`)

| Medida | Definição resumida |
|---|---|
| `Proventos 12m` | `CALCULATE(SUM(f_proventos[valor]), f_proventos[data_pagamento] >= TODAY()-365)` |
| `Preço Atual` | `SELECTEDVALUE(d_empresa[preco_atual])` (fallback `MAX`) |
| `Dividend Yield 12m` | `DIVIDE([Proventos 12m], [Preço Atual])` — formato percentual |

> As medidas de renda variável são independentes das medidas macro (`Valor Atual`, etc.);
> não há soma cross-domínio.

## 7. Report — página nova "Dividendos (Ibovespa)"

Formato PBIR aprimorado, consistente com as páginas existentes.

- **Título** (textbox) + nota da fonte (brapi.dev) e data de referência.
- **Tabela Top 15** (`tableEx`): colunas **Empresa** · **Setor** · **DY 12m**,
  ordenada por `Dividend Yield 12m` desc, com **filtro Top N = 15** por DY.
- **Gráfico de barras** (`barChart`): `Dividend Yield 12m` por `d_empresa[nome]`,
  mesmas 15 empresas (Top N), para leitura rápida.
- **Slicer** (`slicer`) por `d_empresa[setor]`.

## 8. Entregáveis de fechamento

- **README** atualizado: nova seção descrevendo o domínio de dividendos, a fonte brapi,
  o passo de preencher `BrapiToken` localmente, e o lembrete de atualizar `IbovTickers`
  a cada trimestre.
- **.gitignore**: sem mudanças (o cache PBIP já é ignorado).
- Commit da alteração.

## 9. Fora de escopo (YAGNI)

- Histórico de DY ao longo do tempo (só o snapshot 12m atual).
- Outros índices além do Ibovespa (IBRX, SMLL) e outros ativos (FIIs, BDRs).
- Atualização automática da composição do Ibovespa (mantida manual/trimestral).
- Preço médio 12m ou variações do cálculo de DY.
- Publicação/refresh automatizado no Service.

## 10. Critérios de sucesso

1. Abrir o `.pbip` no Power BI Desktop, preencher `BrapiToken` e dar **refresh sem erro**
   contra a API brapi.
2. `d_empresa` traz os ~85 tickers do Ibovespa com setor e preço; `f_proventos` traz os
   proventos do último ano por ticker.
3. A página "Dividendos (Ibovespa)" renderiza a tabela Top 15 (Empresa · Setor · DY 12m),
   o gráfico de barras e o slicer de setor, reagindo entre si.
4. Nenhum token real versionado; repositório limpo.
