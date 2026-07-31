# Panorama Financeiro

Dashboard de portfólio em **Power BI (PBIP/TMDL)** que reúne, num só modelo, dois
domínios de dados públicos do mercado brasileiro:

1. **Macro Brasil (BCB/SGS)** — Selic, CDI, IPCA, IGP-M, câmbio e PIB, via API do
   Banco Central.
2. **Ações do Ibovespa** — dividendos, preço, P/L e faixa de 52 semanas das ações do
   índice, via brapi e Yahoo Finance.

O projeto começou como um panorama puramente macroeconômico e foi **ampliado** para
cobrir também renda variável, tornando-se um panorama financeiro mais completo.

## Fontes de dados

Todas públicas, sem dados sensíveis.

| Domínio | Fonte | Autenticação |
|---|---|---|
| Macro (séries temporais) | BCB SGS — `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json` | Nenhuma |
| Ações — preço, P/L, setor | [brapi.dev](https://brapi.dev) — `/api/quote/{ticker}` e `/api/quote/list` | Token free |
| Ações — dividendos/JCP | Yahoo Finance — `query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1y&events=div` | Nenhuma |

### Séries macro (BCB SGS)

| Código | Indicador            | Frequência |
|-------:|----------------------|------------|
| 432    | Selic Meta           | Diária     |
| 12     | CDI                  | Diária     |
| 433    | IPCA (mensal)        | Mensal     |
| 13522  | IPCA (acum. 12m)     | Mensal     |
| 189    | IGP-M (mensal)       | Mensal     |
| 1      | Dólar PTAX (venda)   | Diária     |
| 4380   | PIB mensal           | Mensal     |

## Modelo

Dois conjuntos de tabelas (star schema) no mesmo modelo semântico:

```
Macro:   d_indicador 1 ── * f_indicadores * ── 1 d_calendario
Ações:   d_empresa   1 ── * f_proventos        (chave: ticker)
```

**Macro**
- `d_indicador` — catálogo de séries (código → nome, unidade, tipo).
- `f_indicadores` — fato longo (`data`, `codigo`, `valor`) alimentado pela função M
  `fnBcbSgs`, que fatia séries diárias em janelas de ≤10 anos (limite da API).
- `d_calendario` — tabela de datas gerada em M.

**Ações**
- `d_empresa` — dimensão por ação (`ticker`, `nome`, `setor`, `preco_atual`, `pl`,
  `min_52s`, `max_52s`), montada pela função M `fnBrapiQuote` (uma chamada brapi por
  ticker) com o setor vindo de `/api/quote/list`.
- `f_proventos` — fato de dividendos/JCP (`ticker`, `data_pagamento`, `valor`, `tipo`),
  alimentado pela função M `fnYahooProventos` (Yahoo Finance).

`_Medidas` reúne as medidas DAX (Valor Atual, Variações, Média, Mín, Máx, Dividend
Yield 12m, etc.).

## Como usar

1. Abra `Panorama Financeiro.pbip` no Power BI Desktop (versão com suporte a PBIP/TMDL).
2. Ao abrir, defina a privacidade das fontes (`api.bcb.gov.br`, `brapi.dev`,
   `query1.finance.yahoo.com`) como **Público**.
3. Preencha o parâmetro `BrapiToken` (veja abaixo).
4. Clique em **Atualizar** para buscar os dados ao vivo das APIs.

## Parâmetros

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `DataInicial` | `2015-01-01` | Início do histórico das séries macro. |
| `UrlBaseBCB` | `https://api.bcb.gov.br` | Base da API do Banco Central. |
| `UrlBaseBrapi` | `https://brapi.dev` | Base da API brapi. |
| `BrapiToken` | `""` | Token free do brapi (**obrigatório** para preço/P/L/setor das ações). |
| `IbovTickers` | carteira do índice | Lista de tickers (Ibovespa + adicionais monitorados). |

> **Nunca comite o token.** O Power BI Desktop reescreve `BrapiToken` com o valor real
> ao salvar; zere para `""` antes de qualquer commit/push. O repositório mantém
> `BrapiToken = ""`.

## Página "Dividendos (Ibovespa)"

Lista as 15 ações do Ibovespa com maior **Dividend Yield dos últimos 12 meses**, com
setor, preço, P/L e faixa de 52 semanas.

- **DY 12m** = (dividendos + JCP pagos nos últimos 12 meses) ÷ preço atual.
- **Dividendos via Yahoo Finance** (grátis, sem token): o plano free do brapi só expõe
  proventos para tickers de sandbox (PETR4, VALE3, MGLU3, ITUB4), então os dividendos de
  todo o universo vêm do Yahoo. Preço, P/L e setor continuam vindo do brapi.
- **Composição do Ibovespa:** atualize o parâmetro `IbovTickers` a cada rebalanceamento
  trimestral da B3.

---

Projeto de portfólio; 100% baseado em dados públicos, sem credenciais versionadas.
