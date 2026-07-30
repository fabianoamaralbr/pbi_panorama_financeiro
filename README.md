# Panorama Macro Brasil (BCB)

Dashboard de portfólio em **Power BI (PBIP/TMDL)** que consome a **API pública do
Banco Central do Brasil** (SGS — Sistema Gerenciador de Séries Temporais) e
apresenta um panorama macroeconômico: Selic, IPCA, câmbio, CDI, IGP-M e PIB.

## Fonte de dados

API pública, sem autenticação:
`https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json`

| Código | Indicador            | Frequência |
|-------:|----------------------|------------|
| 432    | Selic Meta           | Diária     |
| 12     | CDI                  | Diária     |
| 433    | IPCA (mensal)        | Mensal     |
| 13522  | IPCA (acum. 12m)     | Mensal     |
| 189    | IGP-M (mensal)       | Mensal     |
| 1      | Dólar PTAX (venda)   | Diária     |
| 4380   | PIB mensal           | Mensal     |

## Modelo (star schema)

```
d_indicador 1 ── * f_indicadores * ── 1 d_calendario
```

- `d_indicador` — catálogo de séries (código → nome, unidade, tipo).
- `f_indicadores` — fato longo (`data`, `codigo`, `valor`) alimentado pela função M
  `fnBcbSgs`, que fatia séries diárias em janelas de ≤10 anos (limite da API).
- `d_calendario` — tabela de datas gerada em M.
- `_Medidas` — medidas DAX genéricas (Valor Atual, Variações, Média, Mín, Máx).

## Como usar

1. Abra `Panorama Macro BCB.pbip` no Power BI Desktop (versão com suporte a PBIP/TMDL).
2. Ao abrir, defina a privacidade da fonte `api.bcb.gov.br` como **Público**.
3. Clique em **Atualizar** para buscar os dados ao vivo da API.

## Parâmetros

- `DataInicial` (padrão `2015-01-01`) — início do histórico.
- `UrlBaseBCB` (padrão `https://api.bcb.gov.br`).

Projeto sem dados sensíveis; 100% baseado em dados públicos.

## Página "Dividendos (Ibovespa)"

Lista as 15 ações do Ibovespa com maior **Dividend Yield dos últimos 12 meses** e seus setores.

- **Fonte:** API pública [brapi.dev](https://brapi.dev) — setor/preço via `/api/quote/list`, proventos via `/api/quote/{ticker}?dividends=true`.
- **DY 12m** = (dividendos + JCP pagos nos últimos 12 meses) ÷ preço atual.
- **Token (obrigatório):** crie um token free em https://brapi.dev/dashboard e preencha o parâmetro `BrapiToken` em *Transformar dados → Gerenciar parâmetros* no Power BI Desktop. **Nunca** comite o token — o repositório mantém `BrapiToken = ""`.
- **Composição do Ibovespa:** o parâmetro `IbovTickers` traz a carteira atual do índice. Atualize-o a cada rebalanceamento trimestral da B3.
