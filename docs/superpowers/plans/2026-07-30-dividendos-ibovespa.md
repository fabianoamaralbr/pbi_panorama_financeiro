# Dividendos Ibovespa (Top 15 DY) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao projeto `pbi_panorama_macro_bcb` uma página que lista as 15 ações do Ibovespa com maior Dividend Yield dos últimos 12 meses e o setor de cada uma, alimentada pela API pública brapi.dev.

**Architecture:** Estende o SemanticModel existente (star schema BCB) com um domínio de renda variável independente: duas tabelas novas (`d_empresa`, `f_proventos`) importadas via Power Query M do brapi.dev, três medidas DAX de DY, e uma terceira página de report em PBIR. Os dois domínios (macro e ações) coexistem no mesmo modelo sem relacionamento entre si; ambos reusam `d_calendario`.

**Tech Stack:** Power BI PBIP/TMDL (compatibilityLevel 1606), Power Query M (gateway-safe `Web.Contents`), DAX, PBIR enhanced report format. Fonte: API REST brapi.dev (token free).

---

## Nota sobre verificação (PBIP não tem teste automatizado)

Este projeto não possui suíte de testes. A "verificação" de cada tarefa é uma destas, conforme o tipo de artefato:

- **TMDL/JSON**: o arquivo é sintaticamente válido (chaves/indentação corretas, sem quebrar o schema).
- **Modelo (M/DAX)**: abrir `Panorama Macro BCB.pbip` no **Power BI Desktop**, preencher o parâmetro `BrapiToken`, dar **Atualizar** e conferir que a tabela/medida carrega sem erro e com contagem plausível.
- **Report**: abrir o `.pbip`, abrir a nova página e conferir que os visuais renderizam e reagem entre si.

O refresh completo no Desktop é feito **uma vez** na Tarefa 6 (camada de modelo) e **uma vez** na Tarefa 9 (camada de report) — não a cada micro-passo, porque exige o token do usuário e é interativo.

## Pré-requisito do executor

Antes de começar, obter um **token free do brapi** em https://brapi.dev/dashboard (cadastro gratuito). Ele **não** vai para o Git — será digitado no Power BI Desktop no passo de refresh. Se você não tiver o token, execute todas as tarefas de edição de arquivo (1–5, 7–8, 10) e **pule os passos de refresh** (6 e 9), deixando a validação de dados para quem tiver o token.

## File Structure

**Modelo (`Panorama Macro BCB.SemanticModel/definition/`):**
- `expressions.tmdl` — **Modificar**: +3 parâmetros (`UrlBaseBrapi`, `BrapiToken`, `IbovTickers`) e +1 função (`fnBrapiProventos`).
- `tables/d_empresa.tmdl` — **Criar**: dimensão de empresas (ticker, nome, setor, preço).
- `tables/f_proventos.tmdl` — **Criar**: fato de proventos (ticker, data_pagamento, valor, tipo).
- `tables/_Medidas.tmdl` — **Modificar**: +3 medidas de DY.
- `relationships.tmdl` — **Modificar**: +2 relacionamentos.
- `model.tmdl` — **Modificar**: `PBI_QueryOrder` + `ref table` das novas tabelas.

**Report (`Panorama Macro BCB.Report/definition/`):**
- `pages/pages.json` — **Modificar**: incluir a nova página no `pageOrder`.
- `pages/pagina03dividendos/page.json` — **Criar**.
- `pages/pagina03dividendos/visuals/v_titulo_div/visual.json` — **Criar** (textbox).
- `pages/pagina03dividendos/visuals/v_slicer_setor/visual.json` — **Criar** (slicer).
- `pages/pagina03dividendos/visuals/v_tabela_dy/visual.json` — **Criar** (tableEx).
- `pages/pagina03dividendos/visuals/v_bar_dy/visual.json` — **Criar** (barChart).

**Docs:**
- `README.md` — **Modificar**: seção do domínio de dividendos.

---

## Task 1: Parâmetros brapi + função de proventos (camada M)

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/expressions.tmdl`

- [ ] **Step 1: Acrescentar os 3 parâmetros e a função ao fim de `expressions.tmdl`**

Cole o bloco abaixo **após** a linha 63 (depois do `annotation PBI_ResultType = Function` da `fnBcbSgs`, mantendo o resto do arquivo intacto). A lista de tickers do Ibovespa é a semente inicial — atualize-a a cada rebalanceamento trimestral da B3.

```
expression UrlBaseBrapi = "https://brapi.dev" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: b1a7e0c2-2001-4aaa-8bbb-000000000004

	annotation PBI_ResultType = Text

expression BrapiToken = "" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: b1a7e0c2-2001-4aaa-8bbb-000000000005

	annotation PBI_ResultType = Text

/// Tickers do Ibovespa (composição B3). Atualizar a cada rebalanceamento trimestral.
expression IbovTickers = "ABEV3,ALOS3,ASAI3,AURE3,AZUL4,AZZA3,B3SA3,BBAS3,BBDC3,BBDC4,BBSE3,BEEF3,BPAC11,BRAP4,BRAV3,BRFS3,BRKM5,CMIG4,CMIN3,COGN3,CPFE3,CPLE6,CRFB3,CSAN3,CSNA3,CVCB3,CXSE3,CYRE3,EGIE3,ELET3,ELET6,EMBR3,ENGI11,ENEV3,EQTL3,FLRY3,GGBR4,GOAU4,HAPV3,HYPE3,IGTI11,IRBR3,ISAE4,ITSA4,ITUB4,KLBN11,LREN3,MGLU3,MRFG3,MRVE3,MULT3,NATU3,PCAR3,PETR3,PETR4,PETZ3,POMO4,PRIO3,PSSA3,RADL3,RAIL3,RAIZ4,RDOR3,RECV3,RENT3,SANB11,SBSP3,SLCE3,SMTO3,STBP3,SUZB3,TAEE11,TIMS3,TOTS3,UGPA3,USIM5,VALE3,VAMO3,VBBR3,VIVA3,VIVT3,WEGE3,YDUQ3" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: b1a7e0c2-2001-4aaa-8bbb-000000000006

	annotation PBI_ResultType = Text

expression fnBrapiProventos =
		let
		    fnBrapiProventos = (ticker as text) as table =>
		        let
		            resp = Web.Contents(
		                UrlBaseBrapi,
		                [
		                    RelativePath = "api/quote/" & ticker,
		                    Query = [range = "1y", dividends = "true", token = BrapiToken]
		                ]
		            ),
		            json = try Json.Document(resp) otherwise null,
		            resultado = if json = null then null else try json[results]{0} otherwise null,
		            divs = if resultado = null then null else try resultado[dividendsData][cashDividends] otherwise null,
		            vazio = #table(type table [ticker = text, data_pagamento = date, valor = number, tipo = text], {}),
		            tbl =
		                if divs = null or not (divs is list) or List.IsEmpty(divs) then
		                    vazio
		                else
		                    let
		                        recs = Table.FromRecords(divs),
		                        comTicker = Table.AddColumn(recs, "ticker", each ticker, type text),
		                        sel = Table.SelectColumns(comTicker, {"ticker", "paymentDate", "rate", "label"}, MissingField.UseNull),
		                        ren = Table.RenameColumns(sel, {{"paymentDate", "data_pagamento"}, {"rate", "valor"}, {"label", "tipo"}}),
		                        tipos = Table.TransformColumns(
		                            ren,
		                            {
		                                {"data_pagamento", each try Date.FromText(Text.Start(_, 10), [Format="yyyy-MM-dd", Culture="en-US"]) otherwise null, type date},
		                                {"valor", each try Number.From(_) otherwise null, type number},
		                                {"tipo", each if _ <> null and (Text.Contains(Text.Upper(_), "JRS") or Text.Contains(Text.Upper(_), "JCP") or Text.Contains(Text.Upper(_), "CAPITAL")) then "JCP" else "Dividendo", type text}
		                            }
		                        ),
		                        semNulos = Table.SelectRows(tipos, each [data_pagamento] <> null and [valor] <> null)
		                    in
		                        semNulos
		        in
		            tbl
		in
		    fnBrapiProventos
	lineageTag: b1a7e0c2-2001-4aaa-8bbb-000000000007

	annotation PBI_ResultType = Function
```

- [ ] **Step 2: Verificar sintaxe TMDL**

Confira visualmente: cada `expression` tem seu `lineageTag` e `annotation`; a indentação da função usa TAB (igual à `fnBcbSgs` existente); nenhuma linha anterior do arquivo foi alterada.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/expressions.tmdl"
git commit -m "feat(model): parametros brapi e fnBrapiProventos"
```

---

## Task 2: Tabela `d_empresa` (dimensão de empresas)

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/d_empresa.tmdl`

- [ ] **Step 1: Criar `d_empresa.tmdl` com o conteúdo exato**

O endpoint `/api/quote/list` retorna, no free, um array `stocks[]` com `stock`, `name`, `sector`, `close`. Filtramos por `IbovTickers`.

```
table d_empresa
	lineageTag: b1a7e0c2-8001-4aaa-8bbb-000000000001

	column ticker
		dataType: string
		lineageTag: b1a7e0c2-8001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: ticker

		annotation SummarizationSetBy = Automatic

	column nome
		dataType: string
		lineageTag: b1a7e0c2-8001-4aaa-8bbb-000000000003
		summarizeBy: none
		sourceColumn: nome

		annotation SummarizationSetBy = Automatic

	column setor
		dataType: string
		lineageTag: b1a7e0c2-8001-4aaa-8bbb-000000000004
		summarizeBy: none
		sourceColumn: setor

		annotation SummarizationSetBy = Automatic

	column preco_atual
		dataType: double
		formatString: #,0.00
		lineageTag: b1a7e0c2-8001-4aaa-8bbb-000000000005
		summarizeBy: none
		sourceColumn: preco_atual

		annotation SummarizationSetBy = Automatic

	partition d_empresa = m
		mode: import
		source =
				let
				    Alvo = List.Transform(Text.Split(IbovTickers, ","), each Text.Trim(_)),
				    resp = Web.Contents(
				        UrlBaseBrapi,
				        [RelativePath = "api/quote/list", Query = [token = BrapiToken, limit = "1000"]]
				    ),
				    json = Json.Document(resp),
				    stocks = json[stocks],
				    tbl = Table.FromRecords(stocks),
				    sel = Table.SelectColumns(tbl, {"stock", "name", "sector", "close"}, MissingField.UseNull),
				    filtro = Table.SelectRows(sel, each List.Contains(Alvo, [stock])),
				    ren = Table.RenameColumns(filtro, {{"stock", "ticker"}, {"name", "nome"}, {"sector", "setor"}, {"close", "preco_atual"}}),
				    tipos = Table.TransformColumnTypes(ren, {{"ticker", type text}, {"nome", type text}, {"setor", type text}, {"preco_atual", type number}}),
				    semDup = Table.Distinct(tipos, {"ticker"})
				in
				    semDup

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Verificar sintaxe**

Confira que a indentação usa TAB, que `partition d_empresa = m` espelha o padrão de `d_indicador.tmdl`, e que o arquivo termina com o `annotation PBI_ResultType = Table`.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/d_empresa.tmdl"
git commit -m "feat(model): tabela d_empresa (Ibovespa via brapi list)"
```

---

## Task 3: Tabela `f_proventos` (fato de proventos)

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/f_proventos.tmdl`

- [ ] **Step 1: Criar `f_proventos.tmdl` com o conteúdo exato**

```
table f_proventos
	lineageTag: b1a7e0c2-9001-4aaa-8bbb-000000000001

	column ticker
		dataType: string
		lineageTag: b1a7e0c2-9001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: ticker

		annotation SummarizationSetBy = Automatic

	column data_pagamento
		dataType: dateTime
		formatString: Short Date
		lineageTag: b1a7e0c2-9001-4aaa-8bbb-000000000003
		summarizeBy: none
		sourceColumn: data_pagamento

		annotation SummarizationSetBy = Automatic

		annotation UnderlyingDateTimeDataType = Date

	column valor
		dataType: double
		formatString: #,0.00
		lineageTag: b1a7e0c2-9001-4aaa-8bbb-000000000004
		summarizeBy: sum
		sourceColumn: valor

		annotation SummarizationSetBy = Automatic

	column tipo
		dataType: string
		lineageTag: b1a7e0c2-9001-4aaa-8bbb-000000000005
		summarizeBy: none
		sourceColumn: tipo

		annotation SummarizationSetBy = Automatic

	partition f_proventos = m
		mode: import
		source =
				let
				    Tickers = List.Transform(Text.Split(IbovTickers, ","), each Text.Trim(_)),
				    Tabelas = List.Transform(Tickers, each fnBrapiProventos(_)),
				    Combinado = Table.Combine(Tabelas),
				    Tipos = Table.TransformColumnTypes(Combinado, {{"ticker", type text}, {"data_pagamento", type date}, {"valor", type number}, {"tipo", type text}})
				in
				    Tipos

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Verificar sintaxe**

Confira TAB, o bloco `column data_pagamento` com as duas annotations (igual a `f_indicadores[data]`), e o fim com `annotation PBI_ResultType = Table`.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/f_proventos.tmdl"
git commit -m "feat(model): tabela f_proventos (dividendos+JCP via brapi)"
```

---

## Task 4: Registrar tabelas e relacionamentos

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/model.tmdl`
- Modify: `Panorama Macro BCB.SemanticModel/definition/relationships.tmdl`

- [ ] **Step 1: Atualizar `PBI_QueryOrder` em `model.tmdl` (linha 12)**

Substitua a linha inteira:

```
annotation PBI_QueryOrder = ["UrlBaseBCB","DataInicial","fnBcbSgs","d_indicador","f_indicadores","d_calendario","_Medidas"]
```

por:

```
annotation PBI_QueryOrder = ["UrlBaseBCB","DataInicial","fnBcbSgs","UrlBaseBrapi","BrapiToken","IbovTickers","fnBrapiProventos","d_indicador","f_indicadores","d_calendario","d_empresa","f_proventos","_Medidas"]
```

- [ ] **Step 2: Adicionar `ref table` das novas tabelas em `model.tmdl`**

Após a linha `ref table d_calendario` (linha 16), insira duas linhas. Preserve a linha em branco e o `ref cultureInfo pt-BR` no fim do arquivo. O bloco final deve ficar:

```
ref table d_indicador
ref table f_indicadores
ref table d_calendario
ref table d_empresa
ref table f_proventos
ref table _Medidas

ref cultureInfo pt-BR
```

- [ ] **Step 3: Adicionar os 2 relacionamentos em `relationships.tmdl`**

Acrescente ao fim do arquivo (após o relacionamento `...000000000002`):

```
relationship b1a7e0c2-6001-4aaa-8bbb-000000000003
	fromColumn: f_proventos.ticker
	toColumn: d_empresa.ticker

relationship b1a7e0c2-6001-4aaa-8bbb-000000000004
	fromColumn: f_proventos.data_pagamento
	toColumn: d_calendario.data
```

- [ ] **Step 4: Verificar**

`PBI_QueryOrder` lista 13 itens; há 6 linhas `ref table`; `relationships.tmdl` tem 4 relacionamentos. As colunas referenciadas (`f_proventos.ticker`, `d_empresa.ticker`, `f_proventos.data_pagamento`, `d_calendario.data`) existem nas Tarefas 2–3 e no calendário.

- [ ] **Step 5: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/model.tmdl" "Panorama Macro BCB.SemanticModel/definition/relationships.tmdl"
git commit -m "feat(model): registrar d_empresa/f_proventos e relacionamentos"
```

---

## Task 5: Medidas DAX de Dividend Yield

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl`

- [ ] **Step 1: Inserir 3 medidas antes do `partition _Medidas = m`**

Em `_Medidas.tmdl`, insira o bloco abaixo **entre** a medida `Máximo` (termina na linha 53, com `lineageTag ...008`) e o `partition _Medidas = m` (linha 55):

```
	measure 'Proventos 12m' =
			CALCULATE(
			    SUM(f_proventos[valor]),
			    f_proventos[data_pagamento] >= TODAY() - 365
			)
		formatString: #,0.00
		displayFolder: 04. Dividendos
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000009

	measure 'Preço Atual Ação' = SELECTEDVALUE(d_empresa[preco_atual])
		formatString: #,0.00
		displayFolder: 04. Dividendos
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000010

	measure 'Dividend Yield 12m' = DIVIDE([Proventos 12m], [Preço Atual Ação])
		formatString: 0.00%
		displayFolder: 04. Dividendos
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000011
```

- [ ] **Step 2: Verificar**

As 3 medidas usam TAB; `Proventos 12m` referencia `f_proventos[valor]`/`[data_pagamento]` (Tarefa 3); `Preço Atual Ação` referencia `d_empresa[preco_atual]` (Tarefa 2); `Dividend Yield 12m` referencia as duas medidas anteriores pelos nomes exatos. O `partition _Medidas = m` permanece logo abaixo.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl"
git commit -m "feat(model): medidas Proventos 12m, Preco Atual Acao, Dividend Yield 12m"
```

---

## Task 6: Refresh e validação da camada de modelo (Power BI Desktop)

**Files:** nenhum (verificação interativa).

- [ ] **Step 1: Abrir e configurar o token**

Abra `Panorama Macro BCB.pbip` no Power BI Desktop. Em **Transformar dados → Gerenciar parâmetros**, preencha `BrapiToken` com seu token do brapi. **Não salve o token no arquivo versionado** (ver Tarefa 10 / README).

- [ ] **Step 2: Atualizar**

Clique em **Atualizar**. Aguarde as consultas `d_empresa` e `f_proventos` concluírem.

Esperado:
- `d_empresa`: ~80–85 linhas (uma por ticker do Ibovespa encontrado no `list`), com `setor` preenchido e `preco_atual` numérico.
- `f_proventos`: dezenas a centenas de linhas (proventos pagos no último ano pelos tickers), com `data_pagamento` dentro dos últimos 12 meses e `tipo` ∈ {Dividendo, JCP}.
- Sem erro de credencial/anônimo: se aparecer diálogo de autenticação para `brapi.dev`, escolha **Anônimo** (o token vai na query string).

- [ ] **Step 3: Validar as medidas rapidamente**

Crie um visual de tabela temporário (ou use o painel de medidas) com `d_empresa[nome]` e `Dividend Yield 12m`. Confira que valores aparecem como percentuais plausíveis (ex.: 3%–15% para boas pagadoras). Remova o visual temporário depois.

- [ ] **Step 4: Se algo falhar, diagnosticar antes de prosseguir**

- `d_empresa` vazia → confira se os tickers de `IbovTickers` batem com o campo `stock` do `list` (sem sufixos). 
- `f_proventos` vazia → teste a URL de um ticker no navegador: `https://brapi.dev/api/quote/PETR4?range=1y&dividends=true&token=SEU_TOKEN` e confira o caminho `results[0].dividendsData.cashDividends`.
- Rate limit (429) → reduza temporariamente `IbovTickers` a ~10 tickers para validar, depois restaure.

- [ ] **Step 5: Salvar e commitar os metadados do modelo alterados pelo Desktop**

O Desktop pode reescrever `.platform`/`definition.pbism`. Commite **apenas** se as mudanças forem coerentes com esta feature:

```bash
git add "Panorama Macro BCB.SemanticModel/.platform" "Panorama Macro BCB.SemanticModel/definition.pbism"
git commit -m "chore(model): metadados apos refresh do dominio de dividendos"
```

Não commite o parâmetro `BrapiToken` com valor real. Rode `git diff --staged` antes do commit e confirme que `expressions.tmdl` (se aparecer) mantém `BrapiToken = ""`.

---

## Task 7: Criar a página "Dividendos (Ibovespa)"

**Files:**
- Create: `Panorama Macro BCB.Report/definition/pages/pagina03dividendos/page.json`
- Modify: `Panorama Macro BCB.Report/definition/pages/pages.json`

- [ ] **Step 1: Criar `pagina03dividendos/page.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "pagina03dividendos",
  "displayName": "Dividendos (Ibovespa)",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

- [ ] **Step 2: Incluir a página no `pages.json`**

Substitua o conteúdo de `pages/pages.json` por:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
  "pageOrder": [
    "pagina01panorama",
    "pagina02explorar",
    "pagina03dividendos"
  ],
  "activePageName": "pagina01panorama"
}
```

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.Report/definition/pages/pages.json" "Panorama Macro BCB.Report/definition/pages/pagina03dividendos/page.json"
git commit -m "feat(report): pagina Dividendos (Ibovespa)"
```

---

## Task 8: Visuais da página (título, slicer, tabela, barras)

**Files:**
- Create: `.../pagina03dividendos/visuals/v_titulo_div/visual.json`
- Create: `.../pagina03dividendos/visuals/v_slicer_setor/visual.json`
- Create: `.../pagina03dividendos/visuals/v_tabela_dy/visual.json`
- Create: `.../pagina03dividendos/visuals/v_bar_dy/visual.json`

- [ ] **Step 1: Criar `v_titulo_div/visual.json` (textbox)**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "v_titulo_div",
  "position": { "x": 40, "y": 24, "z": 0, "height": 60, "width": 1200, "tabOrder": 0 },
  "visual": {
    "visualType": "textbox",
    "objects": {
      "general": [
        {
          "properties": {
            "paragraphs": [
              {
                "textRuns": [
                  {
                    "value": "Top 15 Dividend Yield — Ibovespa (12 meses)",
                    "textStyle": { "fontSize": "28px", "fontWeight": "bold", "color": "#0D4069" }
                  }
                ]
              }
            ]
          }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 2: Criar `v_slicer_setor/visual.json` (slicer por setor)**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "v_slicer_setor",
  "position": { "x": 40, "y": 100, "z": 0, "height": 520, "width": 300, "tabOrder": 1 },
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "d_empresa" } },
                  "Property": "setor"
                }
              },
              "queryRef": "d_empresa.setor",
              "nativeQueryRef": "setor",
              "active": true
            }
          ]
        }
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 3: Criar `v_tabela_dy/visual.json` (tableEx: Empresa · Setor · DY)**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "v_tabela_dy",
  "position": { "x": 360, "y": 100, "z": 1, "height": 250, "width": 880, "tabOrder": 2 },
  "visual": {
    "visualType": "tableEx",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "d_empresa" } },
                  "Property": "nome"
                }
              },
              "queryRef": "d_empresa.nome",
              "nativeQueryRef": "nome"
            },
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "d_empresa" } },
                  "Property": "setor"
                }
              },
              "queryRef": "d_empresa.setor",
              "nativeQueryRef": "setor"
            },
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "_Medidas" } },
                  "Property": "Dividend Yield 12m"
                }
              },
              "queryRef": "_Medidas.Dividend Yield 12m",
              "nativeQueryRef": "Dividend Yield 12m"
            }
          ]
        }
      }
    },
    "filterConfig": {
      "filters": [
        {
          "name": "f_v_tabela_dy_topn",
          "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_empresa" } }, "Property": "nome" } },
          "type": "TopN",
          "filter": {
            "Version": 2,
            "From": [
              { "Name": "d", "Entity": "d_empresa", "Type": 0 },
              { "Name": "m", "Entity": "_Medidas", "Type": 0 }
            ],
            "Where": [
              {
                "Condition": {
                  "TopN": {
                    "Expressions": [
                      { "Column": { "Expression": { "SourceRef": { "Source": "d" } }, "Property": "nome" } }
                    ],
                    "Top": 15,
                    "OrderBy": [
                      {
                        "Direction": 2,
                        "Expression": { "Measure": { "Expression": { "SourceRef": { "Source": "m" } }, "Property": "Dividend Yield 12m" } }
                      }
                    ]
                  }
                }
              }
            ]
          },
          "howCreated": "User"
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 4: Criar `v_bar_dy/visual.json` (barChart: DY por empresa)**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "v_bar_dy",
  "position": { "x": 360, "y": 360, "z": 2, "height": 260, "width": 880, "tabOrder": 3 },
  "visual": {
    "visualType": "barChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "d_empresa" } },
                  "Property": "nome"
                }
              },
              "queryRef": "d_empresa.nome",
              "nativeQueryRef": "nome",
              "active": true
            }
          ]
        },
        "Y": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "_Medidas" } },
                  "Property": "Dividend Yield 12m"
                }
              },
              "queryRef": "_Medidas.Dividend Yield 12m",
              "nativeQueryRef": "Dividend Yield 12m"
            }
          ]
        }
      }
    },
    "filterConfig": {
      "filters": [
        {
          "name": "f_v_bar_dy_topn",
          "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_empresa" } }, "Property": "nome" } },
          "type": "TopN",
          "filter": {
            "Version": 2,
            "From": [
              { "Name": "d", "Entity": "d_empresa", "Type": 0 },
              { "Name": "m", "Entity": "_Medidas", "Type": 0 }
            ],
            "Where": [
              {
                "Condition": {
                  "TopN": {
                    "Expressions": [
                      { "Column": { "Expression": { "SourceRef": { "Source": "d" } }, "Property": "nome" } }
                    ],
                    "Top": 15,
                    "OrderBy": [
                      {
                        "Direction": 2,
                        "Expression": { "Measure": { "Expression": { "SourceRef": { "Source": "m" } }, "Property": "Dividend Yield 12m" } }
                      }
                    ]
                  }
                }
              }
            ]
          },
          "howCreated": "User"
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 5: Verificar JSON**

Os 4 arquivos são JSON válido (sem vírgula sobrando); `Entity`/`Property` referenciam `d_empresa[nome]`, `d_empresa[setor]` e a medida `Dividend Yield 12m` (nomes exatos das Tarefas 2 e 5).

- [ ] **Step 6: Commit**

```bash
git add "Panorama Macro BCB.Report/definition/pages/pagina03dividendos/visuals"
git commit -m "feat(report): visuais da pagina de dividendos (titulo, slicer, tabela, barras)"
```

---

## Task 9: Verificar a página no Power BI Desktop (interativo)

**Files:** nenhum (verificação; o Top-N já está no JSON da Tarefa 8 via `filterConfig`).

Esta tarefa é feita **pelo usuário** no Power BI Desktop — subagentes não a executam.

- [ ] **Step 1: Abrir a página**

Com o modelo já atualizado (Tarefa 6), abra a página **Dividendos (Ibovespa)**.

- [ ] **Step 2: Conferir renderização e interação**

- A tabela `v_tabela_dy` mostra exatamente **15 linhas** (Empresa · Setor · DY em %), maior DY no topo.
- O gráfico `v_bar_dy` mostra as **mesmas 15 empresas**.
- Clicar num setor no slicer `v_slicer_setor` filtra tabela e gráfico.
- Se o Top-N ou a ordenação não estiverem como esperado, ajuste pela UI (Filtros → N Principais = 15 por `Dividend Yield 12m`; ordenar a coluna DY desc) e salve.

- [ ] **Step 3: Commitar apenas se o Desktop tiver reescrito os visual.json**

Se salvar no Desktop reescrever os arquivos da página (reformatação/ajuste), commite **somente** os arquivos desta feature:

```bash
git add "Panorama Macro BCB.Report/definition/pages/pagina03dividendos"
git commit -m "chore(report): ajustes da pagina de dividendos apos verificacao no Desktop"
```

Rode `git diff --staged --stat` e confirme que só arquivos desta página entraram — **não** commite alterações de whitespace/`filterConfig` de outras páginas (regressão de round-trip do Desktop, como ocorreu antes).

---

## Task 10: Atualizar README e fechamento

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Acrescentar seção ao `README.md`**

Adicione, na seção apropriada do README (após a descrição das séries do BCB), o bloco:

```markdown
## Página "Dividendos (Ibovespa)"

Lista as 15 ações do Ibovespa com maior **Dividend Yield dos últimos 12 meses** e seus setores.

- **Fonte:** API pública [brapi.dev](https://brapi.dev) — setor/preço via `/api/quote/list`, proventos via `/api/quote/{ticker}?dividends=true`.
- **DY 12m** = (dividendos + JCP pagos nos últimos 12 meses) ÷ preço atual.
- **Token (obrigatório):** crie um token free em https://brapi.dev/dashboard e preencha o parâmetro `BrapiToken` em *Transformar dados → Gerenciar parâmetros* no Power BI Desktop. **Nunca** comite o token — o repositório mantém `BrapiToken = ""`.
- **Composição do Ibovespa:** o parâmetro `IbovTickers` traz a carteira atual do índice. Atualize-o a cada rebalanceamento trimestral da B3.
```

- [ ] **Step 2: Verificar**

O README abre a nova seção sem quebrar o índice/formatação existente.

- [ ] **Step 3: Commit final**

```bash
git add README.md
git commit -m "docs: secao da pagina de dividendos no README"
```

---

## Self-Review (executado pelo autor do plano)

**Cobertura do spec:**
- §3 fonte brapi (list + dividends, token, IbovTickers) → Tarefas 1, 2, 3, 6, 10. ✅
- §4 modelagem (d_empresa, f_proventos, relacionamentos, reuso de d_calendario) → Tarefas 2, 3, 4. ✅
- §5 camada M (parâmetros, fnBrapiProventos) → Tarefa 1. ✅
- §6 medidas DAX (Proventos 12m, Preço Atual, Dividend Yield 12m) → Tarefa 5. ✅
- §7 report (título, tabela Top 15, barras, slicer de setor) → Tarefas 7, 8, 9. ✅
- §8 README + token não versionado → Tarefas 6, 10. ✅
- §10 critérios de sucesso (refresh sem erro, ~85 empresas, página renderiza, sem token versionado) → Tarefas 6, 9. ✅

**Consistência de nomes:** `d_empresa[ticker|nome|setor|preco_atual]`, `f_proventos[ticker|data_pagamento|valor|tipo]`, medidas `Proventos 12m` / `Preço Atual Ação` / `Dividend Yield 12m` — usados de forma idêntica entre modelo (Tarefas 2–5) e report (Tarefa 8). ✅

**Placeholders:** nenhum passo de código deixado como "TBD"; a lista `IbovTickers` é uma semente concreta e explicitamente atualizável. O único trabalho de UI (Top-N) está detalhado na Tarefa 9 porque o repo finaliza filtros no Desktop, não em JSON manual. ✅
