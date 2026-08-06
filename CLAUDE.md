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
│       ├── tables/                   # d_indicador, f_indicadores, d_calendario, d_empresa, d_besst, f_proventos, f_proventos_anual, _Medidas
│       │                             # tabelas what-if: p_YieldDesejado, p_Sim_AporteMensal, p_Sim_DYEsperado, p_Sim_CrescAporte, p_Sim_Anos
│       │                             # eixo simulador: d_horizonte
│       └── relationships.tmdl
├── Panorama Macro BCB.Report/        # Camada de relatório (visuais, páginas)
│   └── definition/pages/
│       ├── pagina01panorama/         # KPI cards + linhas: Selic, IPCA, Câmbio, PIB + card Selic (piso yield-alvo)
│       ├── pagina02explorar/         # Exploração livre por indicador (slicer)
│       ├── pagina03dividendos/       # Seleção Barsi (Screener preço-teto/score)
│       ├── pagina04detalhe/          # Detalhe da Ação: 10a de proventos, consistência
│       ├── pagina05ranking/          # Ranking Barsi por Score
│       └── pagina06simulador/        # Simulador de Renda Passiva (bola de neve)
├── contracts/panorama/               # Data contracts (macro + ações)
├── scripts/dq_check_panorama.py      # Validador DQ (dados ao vivo vs contratos)
├── outputs/                          # Relatórios DQ, métricas e decisões
├── docs/superpowers/
│   ├── specs/                        # Design docs das features
│   └── plans/                        # Planos de implementação
└── README.md                         # Documentação completa do projeto
```

**Star schema — domínio Macro:**
`d_indicador` 1 ── * `f_indicadores` * ── 1 `d_calendario`

**Star schema — domínio Ações:**
`d_empresa` 1 ── * `f_proventos` (chave: `ticker`)
`d_empresa` 1 ── * `f_proventos_anual` (chave: `ticker` — Group By de `f_proventos` por ano)
`d_besst` — de-para ticker → sigla BESST (inline M, sem relacionamento formal)

Os dois domínios não têm relacionamento entre si. As tabelas `p_*` (what-if) e `d_horizonte`
(eixo do simulador) não têm relacionamentos — são filtros de medidas via `SELECTEDVALUE`.

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
- **`fnBrapiQuote(ticker)`** — uma chamada brapi por ticker para `d_empresa` (preço, P/L, faixas 52s). O plano **free da brapi não aceita múltiplos tickers por chamada** — batching em lote deixa `d_empresa` vazia; manter 1 requisição/ticker.
- **`fnYahooProventos(ticker)`** — Yahoo Finance para dividendos/JCP de todo o universo Ibovespa (uma chamada por ticker — Yahoo não aceita lote). O brapi free só expõe proventos para 4 tickers sandbox (PETR4, VALE3, MGLU3, ITUB4).
- **`IbovTickers`** — lista estática (~85 tickers). Atualizar manualmente a cada rebalanceamento trimestral da B3.
- **Medidas dedicadas por indicador** (`Selic Meta`, `IPCA 12m`, `Dólar PTAX`, `PIB Mensal`) filtram `d_indicador[codigo]` embutido — os cards/linhas da p1 usam essas medidas, **sem** filtro no visual. Não religar cards a `Valor Atual` sem filtro (soma todos os indicadores).
- **DQ**: contratos em `contracts/panorama/` + validador `scripts/dq_check_panorama.py` (BCB/Yahoo públicos; brapi via `BRAPI_TOKEN` no ambiente). Medidas da pasta "06. Diagnóstico" sinalizam falha parcial de carga.
- **DY 12m** = (dividendos + JCP pagos nos últimos 12 meses) ÷ preço atual.
- **BESST** — mapeamento ticker → sigla (B/E/SA/SE/T/—) curado manualmente em `d_besst` e em `scripts/barsi_calc.BESST_OVERRIDE`. O `setor` da brapi é insuficiente (agrupa banco com seguradora, energia com saneamento) — usar sempre o override por ticker.
- **Preço-teto Barsi** = média de proventos dos últimos **5 anos completos** ÷ yield desejado (janela curta, sensível a mudanças recentes). Consistência (anos consecutivos, cortes, CAGR) usa janela de **10 anos**. As janelas são diferentes por design — ver `outputs/decisions/2026-08-06-camada-barsi.md` decisão (b).
- **`fnYahooProventos`** — desde a Tarefa 2, usa `range=10y` (antes `1y`) para suportar o histórico de 10 anos necessário para as métricas de consistência e o CAGR de dividendos.
- **Oráculo Python**: `scripts/barsi_calc.py` é a fonte de verdade das fórmulas Barsi. As medidas DAX espelham esse código. Para verificar um cenário do simulador, rodar `from scripts.barsi_calc import patrimonio_projetado` diretamente.
- **Auto date/time desligado** (`__PBI_TimeIntelligenceEnabled = 0` em `model.tmdl`) para não inflar o modelo; `d_calendario` é a única tabela de datas. **Marcar `d_calendario` como Tabela de Data no Desktop** (não expresso em TMDL).
- **Sem identidade de marca neste projeto** (portfólio público, decisão do dono). Usar o **tema padrão do Power BI**; não aplicar paleta, fonte, tema customizado nem logomarca corporativa. Decisão documentada em `outputs/decisions/2026-08-06-camada-barsi.md` item (c).

## Gotchas / cuidados

- **`BrapiToken` — NUNCA commitar com valor real.** O Power BI Desktop reescreve o parâmetro com o valor real ao salvar o arquivo. O repositório deve sempre manter `BrapiToken = ""`. **Proteção ativa (`skip-worktree`):** `expressions.tmdl` está marcado com `git update-index --skip-worktree`, então o git ignora as reescritas locais do token — não é mais necessário zerar manualmente antes de commitar. **É config local (não versionada):** em um clone novo/outra máquina, reaplicar com `git update-index --skip-worktree "Panorama Macro BCB.SemanticModel/definition/expressions.tmdl"`. Para commitar mudança legítima nesse arquivo (funções M, `IbovTickers`): `git update-index --no-skip-worktree <arquivo>` → zerar token → commitar → reativar o skip. Um `git pull` que altere esse arquivo pode conflitar — desmarcar antes.
- **Desktop reformata arquivos ao salvar** — pode remover `filterConfig` de cards e alterar formatação de vários `.json`/`.tmdl`. Revisar `git diff` antes de commitar para não incluir ruído de reformatação. **Por isso os cards da p1 usam medidas dedicadas com filtro embutido** (não dependem de `filterConfig` no visual) — foi assim que o bug "todos os cards somando todos os indicadores" foi corrigido.
- **Privacidade das fontes** — se o Desktop pedir configuração de privacidade, todas devem ser **Público**; caso contrário o Power Query bloqueia as queries de combinação.
- **Limite da API BCB** — séries diárias: máximo 10 anos por requisição; `fnBcbSgs` gerencia isso automaticamente com janelas.
- **Composição do Ibovespa** — B3 rebalancea trimestralmente; o parâmetro `IbovTickers` precisa atualização manual. Desde a v2.0 o parâmetro representa o "universo BESST ampliado" (não apenas Ibovespa), mas o nome foi mantido para não quebrar partições M — ver decisão (d) em `outputs/decisions/2026-08-06-camada-barsi.md`.
- **BESST override por ticker** — se um ticker mudar de setor ou uma nova empresa do universo precisar de sigla correta, atualizar `BESST_OVERRIDE` em `scripts/barsi_calc.py` E a tabela inline em `d_besst.tmdl`. As duas fontes devem estar sempre sincronizadas.
- **Teto Barsi = 5 anos; consistência = 10 anos** — não usar 5 anos para métricas de consistência nem 10 anos para o preço-teto. São janelas distintas por design. `f_proventos_anual` armazena todos os anos disponíveis; os filtros de janela vivem nas medidas DAX e no oráculo Python.
- **`range=10y` no Yahoo** — `fnYahooProventos` usa `range=10y` desde a Tarefa 2. Em clones novos ou restauração de função M, conferir que o parâmetro está em `10y` (não `1y`), pois `expressions.tmdl` pode ser restaurado por `git pull` que conflite com o skip-worktree.

## Referências

- `README.md` — documentação completa (fontes, modelo, parâmetros, página de dividendos).
- `docs/superpowers/specs/2026-07-28-panorama-macro-bcb-design.md` — spec da feature macro.
- `docs/superpowers/specs/2026-07-30-dividendos-ibovespa-design.md` — spec da feature dividendos.
- `docs/superpowers/plans/2026-08-06-camada-barsi.md` — plano de implementação da camada Barsi.
- `outputs/decisions/2026-08-06-camada-barsi.md` — registro de decisões técnicas da camada Barsi.
- `scripts/barsi_calc.py` — oráculo Python das fórmulas Barsi (fonte de verdade).
- `tests/test_barsi_calc.py` — testes do oráculo (12 casos).
- `docs/superpowers/plans/` — planos de implementação de cada feature.
- [brapi.dev](https://brapi.dev) — dashboard para gerar/gerenciar token free.
- [BCB SGS](https://www3.bcb.gov.br/sgspub/) — catálogo de séries do Banco Central.
