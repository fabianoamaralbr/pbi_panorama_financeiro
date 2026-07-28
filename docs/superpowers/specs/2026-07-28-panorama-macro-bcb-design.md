# Panorama Macro Brasil (BCB) — Projeto de Portfólio PBIP

**Data:** 2026-07-28
**Autor:** Fabiano Amaral
**Status:** Spec aprovado — pronto para plano de implementação

## 1. Objetivo

Projeto de portfólio público (GitHub) demonstrando, de ponta a ponta, a
competência de um analista de dados sênior: conexão a uma **API pública** (Banco
Central do Brasil — SGS), **modelagem dimensional** (star schema), **DAX** e
**design de relatório** em Power BI, tudo versionado no formato **PBIP/TMDL**.

Tema: **Panorama Macroeconômico do Brasil** — Selic, IPCA, câmbio, CDI, IGP-M e PIB.

## 2. Fonte de dados

API pública **SGS — Sistema Gerenciador de Séries Temporais** do Banco Central:

```
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=dd/MM/yyyy
```

Retorno: array JSON de `{ "data": "dd/MM/yyyy", "valor": "14.25" }` (valor com ponto decimal).
Sem autenticação/chave. Privacidade da fonte = **Público**.

**Restrição confirmada na API real:** séries **diárias** têm limite de **10 anos por
requisição**. Séries mensais não têm essa restrição.

### Séries (Core SGS — códigos validados em 2026-07-28)

| codigo | indicador            | unidade   | tipo   | frequencia | formato   |
|-------:|----------------------|-----------|--------|------------|-----------|
| 432    | Selic Meta           | % a.a.    | Taxa   | Diária     | 0.00 "%"  |
| 12     | CDI                  | % a.d.    | Taxa   | Diária     | 0.000000 "%" |
| 433    | IPCA (mensal)        | % a.m.    | Taxa   | Mensal     | 0.00 "%"  |
| 13522  | IPCA (acum. 12m)     | %         | Taxa   | Mensal     | 0.00 "%"  |
| 189    | IGP-M (mensal)       | % a.m.    | Taxa   | Mensal     | 0.00 "%"  |
| 1      | Dólar PTAX (venda)   | R$        | Preço  | Diária     | 0.0000    |
| 4380   | PIB mensal (val. correntes) | R$ milhões | Índice | Mensal | #,0     |

> `codigo` armazenado como **texto** (chave). CDI (12) é taxa diária; mantido no
> catálogo e pode ser trocado por CDI anualizado (4389) sem mudar o modelo.

## 3. Abordagem de modelagem — Star schema com fato único (Abordagem A)

Fato único no formato **longo** + dimensões. Adicionar uma série nova = **1 linha**
em `d_indicador`. Escolhida sobre a alternativa "uma tabela por indicador" (flat,
repetitiva) por ser DRY, escalável e demonstrar maturidade de modelagem.

```
d_indicador (codigo, indicador, unidade, tipo, frequencia, ordem, formato, data_inicial)
      │ 1
      │
      │ *
f_indicadores (data, codigo, valor)
      │ *
      │
      │ 1
d_calendario (data, ano, mes, nomemes, trimestre, anomes, mesano)
```

**Relacionamentos:**
- `f_indicadores[codigo]` → `d_indicador[codigo]` (muitos-para-um, filtro único)
- `f_indicadores[data]`   → `d_calendario[data]` (muitos-para-um, filtro único)

## 4. Formato do artefato PBIP

Espelha as convenções observadas em `pbi_acelerar_comercial`:

- **SemanticModel** em TMDL: `database.tmdl` (compatibilityLevel 1606),
  `model.tmdl` (culture pt-BR, `PBI_QueryOrder`), `relationships.tmdl`,
  `expressions.tmdl` (parâmetros + função), `tables/*.tmdl` (partições `mode: import`).
- **Report** "fino" no formato PBIR aprimorado (report.json 3.3.0, pages/ com
  page.json + visuals/*/visual.json), referenciando o modelo por caminho
  (`definition.pbir` → `byPath`), como no `relatorio_acelerar_comercial`.

### Estrutura de pastas

```
pbi_panorama_macro_bcb/
├─ Panorama Macro BCB.pbip
├─ Panorama Macro BCB.SemanticModel/
│  ├─ .platform
│  ├─ definition.pbism
│  └─ definition/
│     ├─ database.tmdl
│     ├─ model.tmdl
│     ├─ relationships.tmdl
│     ├─ expressions.tmdl
│     └─ tables/
│        ├─ d_indicador.tmdl
│        ├─ f_indicadores.tmdl
│        ├─ d_calendario.tmdl
│        └─ _Medidas.tmdl
├─ Panorama Macro BCB.Report/
│  ├─ .platform
│  ├─ definition.pbir
│  └─ definition/
│     ├─ report.json
│     ├─ version.json
│     └─ pages/
│        ├─ pages.json
│        ├─ <pagina1>/page.json + visuals/*
│        └─ <pagina2>/page.json + visuals/*
├─ docs/…/2026-07-28-panorama-macro-bcb-design.md   (este spec)
├─ README.md
└─ .gitignore
```

## 5. Camada M (`expressions.tmdl`)

- **Parâmetro** `DataInicial` (Text, default `"2015-01-01"`).
- **Parâmetro** `UrlBaseBCB` (Text, default `"https://api.bcb.gov.br"`).
- **Função** `fnBcbSgs(codigo as text, dataInicial as text) as table`:
  - Fatiar `[dataInicial, hoje]` em janelas de **≤10 anos** (respeita limite diário).
  - Para cada janela: `Web.Contents(UrlBaseBCB, [RelativePath="dados/serie/bcdata.sgs."
    & codigo & "/dados", Query=[formato="json", dataInicial=..., dataFinal=...]])`
    — padrão **gateway-safe** (RelativePath/Query separados) para refresh no Service.
  - `Json.Document` → `data` para `type date` (cultura pt-BR, `dd/MM/yyyy`) e
    `valor` para `type number` (cultura invariante, ponto decimal).
  - `Table.Combine` das janelas + `Table.Distinct` por `data`.

`f_indicadores` percorre `d_indicador` (lista de códigos, data-driven), chama
`fnBcbSgs` por código, adiciona coluna `codigo` e empilha (`Table.Combine`).

`d_calendario` gerado em M de `min(f_indicadores[data])` até hoje.

## 6. Medidas DAX (`_Medidas`)

Genéricas — reagem ao indicador em contexto (slicer/filtro de card):

| Medida               | Definição resumida |
|----------------------|--------------------|
| `Valor Atual`        | valor na `MAX(d_calendario[data])` com dado |
| `Data de Referência` | `MAX` da data com valor no contexto |
| `Variação no Mês`    | atual − valor do mês anterior |
| `Variação 12 Meses`  | atual − valor 12 meses antes |
| `Média no Período`   | `AVERAGE(f_indicadores[valor])` |
| `Mínimo` / `Máximo`  | `MIN`/`MAX(f_indicadores[valor])` |

> Não há medida de soma cross-indicador (unidades distintas): o painel sempre
> fatia por um indicador.

## 7. Report (2 páginas — formato PBIR do relatorio_acelerar_comercial)

**Página 1 — "Panorama Macro":** título (textbox) + 4 cards KPI (Selic, IPCA 12m,
Dólar, PIB) — cada card com filtro de visual fixo por `codigo` — + mini line charts
por indicador (um gráfico por unidade, para não misturar escalas).

**Página 2 — "Explorar Indicador":** slicer em `d_indicador[indicador]` + line chart
(`valor` × `d_calendario[mesano]`) + cards (Valor Atual, Variação 12 Meses, Máximo,
Mínimo) + tabela de série.

Visuais usam `cardVisual`, `lineChart`, `slicer`, `tableEx`, `textbox` no schema
`visualContainer` observado no repo de referência.

## 8. Entregáveis de fechamento

- **README.md** (pt-BR): descrição, fonte pública (BCB/SGS), diagrama do modelo,
  lista de séries, instruções de refresh no Power BI Desktop, print/gif opcional.
- **.gitignore**: ignora `.pbi/cache.abf`, `.pbi/localSettings.json`, `*.abf`.
- **git init** + commit inicial. **Push para o GitHub**: passo os comandos ao
  usuário (ou via `gh` se autenticado) — requer a conta dele.

## 9. Fora de escopo (YAGNI)

- Família OData/Focus (expectativas) — fica para evolução futura.
- Field parameters / troca dinâmica de indicador (Abordagem C).
- RLS, temas customizados, bookmarks, drill-through.
- Publicação/refresh automatizado no Service (só deixamos o modelo compatível).

## 10. Critérios de sucesso

1. Abrir o `.pbip` no Power BI Desktop e dar **refresh sem erro** contra a API real.
2. `f_indicadores` traz as 7 séries com histórico (diárias completas via janelas).
3. As 2 páginas renderizam cards e gráficos reagindo ao indicador.
4. Repositório limpo, com README e sem cache versionado.
```
