# pbi_panorama_financeiro — Dashboard Power BI de macro e renda variável via APIs públicas

> Primer de contexto para o Claude Code. Herda de `../CLAUDE.md` (repos) e `../data_squad/CLAUDE.md` (Data Squad). NÃO repetir catálogo Fabric nem convenções globais.

## Propósito

Projeto de portfólio público (GitHub) que demonstra conexão a APIs públicas, modelagem dimensional (star schema), DAX e design de relatório em Power BI, tudo versionado em formato **PBIP/TMDL**. Dois domínios coexistem no mesmo modelo semântico:

1. **Macro Brasil (BCB/SGS)** — Selic, CDI, IPCA, IGP-M, câmbio (PTAX) e PIB.
2. **Ações do Ibovespa** — dividendos/JCP, preço, P/L e faixa 52 semanas.

Sem dados sensíveis ou credenciais fixas (exceto `BrapiToken` — ver Gotchas).

## Stack

- **Power BI Desktop** — formato **PBIP/TMDL** (versão com suporte a PBIP obrigatória).
- **Power Query (M)** — toda ingestão de dados via funções M customizadas.
- **DAX** — medidas em tabela `_Medidas`.
- **Fontes de dados** (todas públicas):

| Fonte | URL | Auth |
|---|---|---|
| BCB SGS (macro) | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados` | Nenhuma |
| brapi.dev (preço/P/L/setor) | `https://brapi.dev/api/quote/{ticker}` e `/api/quote/list` | Token free (`BrapiToken`) |
| Yahoo Finance (dividendos) | `https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA` | Nenhuma |

## Estrutura

```
pbi_panorama_financeiro/
├── Panorama Financeiro.pbip          # Arquivo de entrada — abrir no Desktop
├── Panorama Macro BCB.SemanticModel/ # Modelo semântico (tabelas, funções M, parâmetros, medidas)
│   └── definition/
│       ├── expressions.tmdl          # Parâmetros + funções M (fnBcbSgs, fnBrapiQuote, fnYahooProventos)
│       ├── tables/                   # d_indicador, f_indicadores, d_calendario, d_empresa, f_proventos, _Medidas
│       └── relationships.tmdl
├── Panorama Macro BCB.Report/        # Camada de relatório (visuais, páginas)
│   └── definition/pages/
│       ├── pagina01panorama/         # KPI cards + linhas: Selic, IPCA, Câmbio, PIB
│       ├── pagina02explorar/         # Exploração livre por indicador (slicer)
│       └── pagina03dividendos/       # Top 15 DY 12m Ibovespa
├── docs/superpowers/
│   ├── specs/                        # Design docs das features
│   └── plans/                        # Planos de implementação
└── README.md                         # Documentação completa do projeto
```

**Star schema — domínio Macro:**
`d_indicador` 1 ── * `f_indicadores` * ── 1 `d_calendario`

**Star schema — domínio Ações:**
`d_empresa` 1 ── * `f_proventos` (chave: `ticker`)

Os dois domínios não têm relacionamento entre si.

## Fluxo principal / como abrir e editar

1. Abrir `Panorama Financeiro.pbip` no Power BI Desktop (versão com suporte PBIP/TMDL).
2. Definir privacidade das três fontes (`api.bcb.gov.br`, `brapi.dev`, `query1.finance.yahoo.com`) como **Público**.
3. Preencher o parâmetro `BrapiToken` com o token free do brapi.dev.
4. Clicar em **Atualizar** para buscar dados ao vivo.

**Editar funções M / parâmetros:** `Panorama Macro BCB.SemanticModel/definition/expressions.tmdl`
**Editar medidas DAX:** tabela `_Medidas` em `definition/tables/_Medidas.tmdl`
**Editar visuais/páginas:** arquivos `visual.json` dentro de `Panorama Macro BCB.Report/definition/pages/`

## Convenções específicas

- **`fnBcbSgs(codigo, dataInicial)`** — fatia séries diárias em janelas de ≤10 anos (limite da API BCB). Séries mensais não têm essa restrição.
- **`fnBrapiQuote(ticker)`** — uma chamada brapi por ticker para `d_empresa` (preço, P/L, faixas 52s).
- **`fnYahooProventos(ticker)`** — Yahoo Finance para dividendos/JCP de todo o universo Ibovespa. O brapi free só expõe proventos para 4 tickers sandbox (PETR4, VALE3, MGLU3, ITUB4).
- **`IbovTickers`** — lista estática (~85 tickers). Atualizar manualmente a cada rebalanceamento trimestral da B3.
- **DY 12m** = (dividendos + JCP pagos nos últimos 12 meses) ÷ preço atual.
- Sem identidade de marca corporativa (tema padrão do Power BI).

## Gotchas / cuidados

- **`BrapiToken` — NUNCA commitar com valor real.** O Power BI Desktop reescreve o parâmetro com o valor real ao salvar o arquivo. Zerar para `""` antes de qualquer `git commit` ou `git push`. O repositório deve sempre manter `BrapiToken = ""`.
- **Desktop reformata arquivos ao salvar** — pode remover `filterConfig` de cards e alterar formatação de vários `.json`/`.tmdl`. Revisar `git diff` antes de commitar para não incluir ruído de reformatação.
- **Privacidade das fontes** — se o Desktop pedir configuração de privacidade, todas devem ser **Público**; caso contrário o Power Query bloqueia as queries de combinação.
- **Limite da API BCB** — séries diárias: máximo 10 anos por requisição; `fnBcbSgs` gerencia isso automaticamente com janelas.
- **Composição do Ibovespa** — B3 rebalancea trimestralmente; o parâmetro `IbovTickers` precisa atualização manual.

## Referências

- `README.md` — documentação completa (fontes, modelo, parâmetros, página de dividendos).
- `docs/superpowers/specs/2026-07-28-panorama-macro-bcb-design.md` — spec da feature macro.
- `docs/superpowers/specs/2026-07-30-dividendos-ibovespa-design.md` — spec da feature dividendos.
- `docs/superpowers/plans/` — planos de implementação de cada feature.
- [brapi.dev](https://brapi.dev) — dashboard para gerar/gerenciar token free.
- [BCB SGS](https://www3.bcb.gov.br/sgspub/) — catálogo de séries do Banco Central.
