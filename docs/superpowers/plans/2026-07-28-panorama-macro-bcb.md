# Panorama Macro Brasil (BCB) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portfolio-grade Power BI PBIP project (TMDL semantic model + PBIR report) that connects to the public Banco Central SGS API and presents a Brazilian macroeconomic panel.

**Architecture:** Star schema with a single long fact `f_indicadores` fed by an M function `fnBcbSgs` (10-year windowing for daily series, gateway-safe `Web.Contents`), a data-driven `d_indicador` catalog, a generated `d_calendario`, generic DAX measures in `_Medidas`, and a 2-page PBIR report mirroring the `relatorio_acelerar_comercial` format.

**Tech Stack:** Power BI PBIP (TMDL 1606 / PBIR 3.3.0), Power Query M, DAX, BCB SGS REST API (JSON), git.

---

## Working directory

All paths below are relative to `C:\Users\Fabiano Amaral\repos\pbi_panorama_macro_bcb\`.
This folder already contains `docs/superpowers/specs/2026-07-28-panorama-macro-bcb-design.md`.

## Notes on verification in this domain

There is **no unit-test framework** for PBIP. Verification per task uses:
- **JSON validity:** `python -m json.tool <file> > /dev/null` (must exit 0).
- **Structural greps:** confirm required tokens exist.
- **API reality check:** `curl` against the live SGS endpoint (already validated 2026-07-28).
- **Acceptance (manual, by the user):** open `Panorama Macro BCB.pbip` in Power BI Desktop and press **Refresh** — this is the definitive test and is listed in the final task.

## File Structure

- `Panorama Macro BCB.pbip` — PBIP entry (points to the Report artifact).
- `Panorama Macro BCB.SemanticModel/` — TMDL model.
  - `.platform`, `definition.pbism`, `definition/database.tmdl`, `definition/model.tmdl`, `definition/relationships.tmdl`, `definition/expressions.tmdl`.
  - `definition/tables/`: `d_indicador.tmdl`, `f_indicadores.tmdl`, `d_calendario.tmdl`, `_Medidas.tmdl`.
- `Panorama Macro BCB.Report/` — PBIR report.
  - `.platform`, `definition.pbir`, `definition/report.json`, `definition/version.json`, `definition/pages/pages.json`, `definition/pages/<page>/page.json`, `definition/pages/<page>/visuals/<v>/visual.json`.
- `README.md`, `.gitignore`.

Each `lineageTag` GUID must be unique. Use the literal GUIDs given in this plan (they are pre-generated and internally consistent).

---

### Task 1: Project scaffold, .gitignore, git init

**Files:**
- Create: `.gitignore`
- Create: `README.md` (skeleton; finalized in Task 13)

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Power BI local cache / user settings
**/.pbi/cache.abf
**/.pbi/localSettings.json
**/*.abf
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Create `README.md` skeleton**

```markdown
# Panorama Macro Brasil (BCB)

Projeto de portfólio em Power BI (PBIP/TMDL) conectando a API pública do Banco
Central do Brasil (SGS). Conteúdo detalhado adicionado ao final da construção.
```

- [ ] **Step 3: Initialize git and commit**

Run:
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
git init
git add .gitignore README.md docs
git commit -m "chore: scaffold panorama macro bcb portfolio project"
```
Expected: repository initialized, one commit created.

---

### Task 2: Semantic model skeleton (PBIP + platform + database)

**Files:**
- Create: `Panorama Macro BCB.pbip`
- Create: `Panorama Macro BCB.SemanticModel/.platform`
- Create: `Panorama Macro BCB.SemanticModel/definition.pbism`
- Create: `Panorama Macro BCB.SemanticModel/definition/database.tmdl`

- [ ] **Step 1: Create `Panorama Macro BCB.pbip`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [
    {
      "report": {
        "path": "Panorama Macro BCB.Report"
      }
    }
  ],
  "settings": {
    "enableAutoRecovery": true
  }
}
```

- [ ] **Step 2: Create `Panorama Macro BCB.SemanticModel/.platform`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "SemanticModel",
    "displayName": "Panorama Macro BCB"
  },
  "config": {
    "version": "2.0",
    "logicalId": "b1a7e0c2-1111-4aaa-8bbb-000000000001"
  }
}
```

- [ ] **Step 3: Create `Panorama Macro BCB.SemanticModel/definition.pbism`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  "version": "4.2",
  "settings": {}
}
```

- [ ] **Step 4: Create `Panorama Macro BCB.SemanticModel/definition/database.tmdl`**

```tmdl
database
	compatibilityLevel: 1606
```

- [ ] **Step 5: Verify JSON validity**

Run:
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
python -m json.tool "Panorama Macro BCB.pbip" > /dev/null && \
python -m json.tool "Panorama Macro BCB.SemanticModel/.platform" > /dev/null && \
python -m json.tool "Panorama Macro BCB.SemanticModel/definition.pbism" > /dev/null && echo OK
```
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add "Panorama Macro BCB.pbip" "Panorama Macro BCB.SemanticModel/.platform" "Panorama Macro BCB.SemanticModel/definition.pbism" "Panorama Macro BCB.SemanticModel/definition/database.tmdl"
git commit -m "feat: add pbip entry and semantic model skeleton"
```

---

### Task 3: Data-source parameters + `fnBcbSgs` (expressions.tmdl)

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/expressions.tmdl`

- [ ] **Step 1: Write `expressions.tmdl`**

```tmdl
expression UrlBaseBCB = "https://api.bcb.gov.br" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: b1a7e0c2-2001-4aaa-8bbb-000000000001

	annotation PBI_ResultType = Text

expression DataInicial = "2015-01-01" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: b1a7e0c2-2001-4aaa-8bbb-000000000002

	annotation PBI_ResultType = Text

expression fnBcbSgs =
		let
		    fnBcbSgs = (codigo as text, dataInicial as text) as table =>
		        let
		            DataFim = Date.From(DateTime.LocalNow()),
		            DataIni = Date.FromText(dataInicial, [Format="yyyy-MM-dd", Culture="en-US"]),
		            AnosTotais = Duration.TotalDays(DataFim - DataIni) / 365,
		            NumJanelas = List.Max({1, Number.RoundUp(AnosTotais / 10)}),
		            Janelas = List.Transform(
		                {0..NumJanelas - 1},
		                (i) =>
		                    let
		                        ini = Date.AddYears(DataIni, i * 10),
		                        fimBruto = Date.AddDays(Date.AddYears(ini, 10), -1),
		                        fim = if fimBruto > DataFim then DataFim else fimBruto
		                    in
		                        [ini = ini, fim = fim]
		            ),
		            BuscaJanela = (jan as record) as table =>
		                let
		                    resp = Web.Contents(
		                        UrlBaseBCB,
		                        [
		                            RelativePath = "dados/serie/bcdata.sgs." & codigo & "/dados",
		                            Query = [
		                                formato = "json",
		                                dataInicial = Date.ToText(jan[ini], [Format="dd/MM/yyyy", Culture="pt-BR"]),
		                                dataFinal = Date.ToText(jan[fim], [Format="dd/MM/yyyy", Culture="pt-BR"])
		                            ]
		                        ]
		                    ),
		                    json = try Json.Document(resp) otherwise null,
		                    tbl =
		                        if json = null or not (json is list) or List.IsEmpty(json) then
		                            #table(type table [data = text, valor = text], {})
		                        else
		                            Table.FromRecords(json)
		                in
		                    tbl,
		            Combinado = Table.Combine(List.Transform(Janelas, each BuscaJanela(_))),
		            ComData = Table.TransformColumns(Combinado, {{"data", each Date.FromText(_, [Format="dd/MM/yyyy", Culture="pt-BR"]), type date}}),
		            ComValor = Table.TransformColumns(ComData, {{"valor", each Number.FromText(_, "en-US"), type number}}),
		            SemDup = Table.Distinct(ComValor, {"data"}),
		            Ordenado = Table.Sort(SemDup, {{"data", Order.Ascending}})
		        in
		            Ordenado
		in
		    fnBcbSgs
	lineageTag: b1a7e0c2-2001-4aaa-8bbb-000000000003

	annotation PBI_ResultType = Function
```

- [ ] **Step 2: Verify the M mirrors the validated API contract**

Run (sanity check the endpoint the function targets still returns `{data,valor}`):
```bash
curl -s --max-time 20 "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01/01/2015&dataFinal=31/12/2024" | head -c 120; echo
```
Expected: starts with `[{"data":"...","valor":"..."}`.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/expressions.tmdl"
git commit -m "feat: add BCB SGS parameters and fnBcbSgs windowed fetch function"
```

---

### Task 4: `d_indicador` dimension (catalog)

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/d_indicador.tmdl`

- [ ] **Step 1: Write `d_indicador.tmdl`**

```tmdl
table d_indicador
	lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000001

	column codigo
		dataType: string
		lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: codigo

		annotation SummarizationSetBy = Automatic

	column indicador
		dataType: string
		lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000003
		summarizeBy: none
		sourceColumn: indicador

		annotation SummarizationSetBy = Automatic

	column unidade
		dataType: string
		lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000004
		summarizeBy: none
		sourceColumn: unidade

		annotation SummarizationSetBy = Automatic

	column tipo
		dataType: string
		lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000005
		summarizeBy: none
		sourceColumn: tipo

		annotation SummarizationSetBy = Automatic

	column frequencia
		dataType: string
		lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000006
		summarizeBy: none
		sourceColumn: frequencia

		annotation SummarizationSetBy = Automatic

	column ordem
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000007
		summarizeBy: none
		sourceColumn: ordem

		annotation SummarizationSetBy = Automatic

	column data_inicial
		dataType: string
		lineageTag: b1a7e0c2-3001-4aaa-8bbb-000000000008
		summarizeBy: none
		sourceColumn: data_inicial

		annotation SummarizationSetBy = Automatic

	partition d_indicador = m
		mode: import
		source =
				let
				    Fonte = #table(
				        type table [codigo = text, indicador = text, unidade = text, tipo = text, frequencia = text, ordem = Int64.Type, data_inicial = text],
				        {
				            {"432", "Selic Meta", "% a.a.", "Taxa", "Diária", 1, DataInicial},
				            {"12", "CDI", "% a.d.", "Taxa", "Diária", 2, DataInicial},
				            {"433", "IPCA (mensal)", "% a.m.", "Taxa", "Mensal", 3, DataInicial},
				            {"13522", "IPCA (acum. 12m)", "%", "Taxa", "Mensal", 4, DataInicial},
				            {"189", "IGP-M (mensal)", "% a.m.", "Taxa", "Mensal", 5, DataInicial},
				            {"1", "Dólar PTAX (venda)", "R$", "Preço", "Diária", 6, DataInicial},
				            {"4380", "PIB mensal", "R$ milhões", "Índice", "Mensal", 7, DataInicial}
				        }
				    )
				in
				    Fonte

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Verify structure**

Run:
```bash
grep -c "column " "Panorama Macro BCB.SemanticModel/definition/tables/d_indicador.tmdl"
```
Expected: `7`.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/d_indicador.tmdl"
git commit -m "feat: add d_indicador catalog dimension"
```

---

### Task 5: `f_indicadores` fact

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/f_indicadores.tmdl`

- [ ] **Step 1: Write `f_indicadores.tmdl`**

```tmdl
table f_indicadores
	lineageTag: b1a7e0c2-4001-4aaa-8bbb-000000000001

	column codigo
		dataType: string
		lineageTag: b1a7e0c2-4001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: codigo

		annotation SummarizationSetBy = Automatic

	column data
		dataType: dateTime
		formatString: Short Date
		lineageTag: b1a7e0c2-4001-4aaa-8bbb-000000000003
		summarizeBy: none
		sourceColumn: data

		annotation SummarizationSetBy = Automatic

		annotation UnderlyingDateTimeDataType = Date

	column valor
		dataType: double
		lineageTag: b1a7e0c2-4001-4aaa-8bbb-000000000004
		summarizeBy: sum
		sourceColumn: valor

		annotation SummarizationSetBy = Automatic

	partition f_indicadores = m
		mode: import
		source =
				let
				    Codigos = d_indicador,
				    ComSerie = Table.AddColumn(Codigos, "serie", each fnBcbSgs([codigo], [data_inicial]), type table),
				    Selecao = Table.SelectColumns(ComSerie, {"codigo", "serie"}),
				    Expandido = Table.ExpandTableColumn(Selecao, "serie", {"data", "valor"}, {"data", "valor"}),
				    Tipos = Table.TransformColumnTypes(Expandido, {{"codigo", type text}, {"data", type date}, {"valor", type number}})
				in
				    Tipos

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Verify structure**

Run:
```bash
grep -q "fnBcbSgs(\[codigo\]" "Panorama Macro BCB.SemanticModel/definition/tables/f_indicadores.tmdl" && echo OK
```
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/f_indicadores.tmdl"
git commit -m "feat: add f_indicadores long fact fed by fnBcbSgs"
```

---

### Task 6: `d_calendario` generated date table

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/d_calendario.tmdl`

- [ ] **Step 1: Write `d_calendario.tmdl`**

```tmdl
table d_calendario
	lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000001
	dataCategory: Time

	column data
		isKey
		dataType: dateTime
		formatString: Short Date
		lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: data

		annotation SummarizationSetBy = Automatic

		annotation UnderlyingDateTimeDataType = Date

	column ano
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000003
		summarizeBy: none
		sourceColumn: ano

		annotation SummarizationSetBy = Automatic

	column mes
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000004
		summarizeBy: none
		sourceColumn: mes

		annotation SummarizationSetBy = Automatic

	column nomemes
		dataType: string
		lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000005
		summarizeBy: none
		sourceColumn: nomemes

		annotation SummarizationSetBy = Automatic

	column trimestre
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000006
		summarizeBy: none
		sourceColumn: trimestre

		annotation SummarizationSetBy = Automatic

	column anomes
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000007
		summarizeBy: none
		sourceColumn: anomes

		annotation SummarizationSetBy = Automatic

	column mesano
		dataType: string
		lineageTag: b1a7e0c2-5001-4aaa-8bbb-000000000008
		summarizeBy: none
		sourceColumn: mesano
		sortByColumn: anomes

		annotation SummarizationSetBy = Automatic

	partition d_calendario = m
		mode: import
		source =
				let
				    MinData = List.Min(f_indicadores[data]),
				    MaxData = Date.From(DateTime.LocalNow()),
				    Dias = List.Dates(MinData, Duration.Days(MaxData - MinData) + 1, #duration(1, 0, 0, 0)),
				    Tabela = Table.FromList(Dias, Splitter.SplitByNothing(), {"data"}),
				    ComTipo = Table.TransformColumnTypes(Tabela, {{"data", type date}}),
				    Ano = Table.AddColumn(ComTipo, "ano", each Date.Year([data]), Int64.Type),
				    Mes = Table.AddColumn(Ano, "mes", each Date.Month([data]), Int64.Type),
				    NomeMes = Table.AddColumn(Mes, "nomemes", each Date.ToText([data], [Format="MMM", Culture="pt-BR"]), type text),
				    Trim = Table.AddColumn(NomeMes, "trimestre", each Date.QuarterOfYear([data]), Int64.Type),
				    AnoMes = Table.AddColumn(Trim, "anomes", each [ano] * 100 + [mes], Int64.Type),
				    MesAno = Table.AddColumn(AnoMes, "mesano", each Text.PadStart(Text.From([mes]), 2, "0") & "/" & Text.From([ano]), type text)
				in
				    MesAno

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Verify structure**

Run:
```bash
grep -c "column " "Panorama Macro BCB.SemanticModel/definition/tables/d_calendario.tmdl"
```
Expected: `7`.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/d_calendario.tmdl"
git commit -m "feat: add generated d_calendario date table"
```

---

### Task 7: Relationships

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/relationships.tmdl`

- [ ] **Step 1: Write `relationships.tmdl`**

```tmdl
relationship b1a7e0c2-6001-4aaa-8bbb-000000000001
	fromColumn: f_indicadores.codigo
	toColumn: d_indicador.codigo

relationship b1a7e0c2-6001-4aaa-8bbb-000000000002
	fromColumn: f_indicadores.data
	toColumn: d_calendario.data
```

- [ ] **Step 2: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/relationships.tmdl"
git commit -m "feat: relate f_indicadores to d_indicador and d_calendario"
```

---

### Task 8: `_Medidas` measures table (DAX)

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl`

- [ ] **Step 1: Write `_Medidas.tmdl`**

The partition uses the same empty single-column deflate blob used by the reference model (`i44FAA==`).

```tmdl
table _Medidas
	lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000001

	measure 'Valor Atual' =
			CALCULATE(
			    SUM(f_indicadores[valor]),
			    LASTNONBLANK(d_calendario[data], CALCULATE(SUM(f_indicadores[valor])))
			)
		formatString: #,0.00
		displayFolder: 01. Base
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000002

	measure 'Data de Referência' = CALCULATE(MAX(f_indicadores[data]))
		formatString: Short Date
		displayFolder: 01. Base
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000003

	measure 'Variação no Mês' =
			VAR _dataRef = [Data de Referência]
			VAR _atual = [Valor Atual]
			VAR _anterior =
			    CALCULATE([Valor Atual], d_calendario[data] <= EDATE(_dataRef, -1))
			RETURN
			    _atual - _anterior
		formatString: #,0.00
		displayFolder: 02. Variação
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000004

	measure 'Variação 12 Meses' =
			VAR _dataRef = [Data de Referência]
			VAR _atual = [Valor Atual]
			VAR _anterior =
			    CALCULATE([Valor Atual], d_calendario[data] <= EDATE(_dataRef, -12))
			RETURN
			    _atual - _anterior
		formatString: #,0.00
		displayFolder: 02. Variação
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000005

	measure 'Média no Período' = AVERAGE(f_indicadores[valor])
		formatString: #,0.00
		displayFolder: 03. Estatística
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000006

	measure 'Mínimo' = MIN(f_indicadores[valor])
		formatString: #,0.00
		displayFolder: 03. Estatística
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000007

	measure 'Máximo' = MAX(f_indicadores[valor])
		formatString: #,0.00
		displayFolder: 03. Estatística
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000008

	partition _Medidas = m
		mode: import
		source =
				let
				    Fonte = Table.FromRows(Json.Document(Binary.Decompress(Binary.FromText("i44FAA==", BinaryEncoding.Base64), Compression.Deflate)), let _t = ((type nullable text) meta [Serialized.Text = true]) in type table [#"Coluna 1" = _t]),
				    #"Tipo Alterado" = Table.TransformColumnTypes(Fonte, {{"Coluna 1", type text}})
				in
				    #"Tipo Alterado"

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Verify structure**

Run:
```bash
grep -c "measure " "Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl"
```
Expected: `7`.

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl"
git commit -m "feat: add generic macro measures in _Medidas"
```

---

### Task 9: `model.tmdl` (wire tables + query order)

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/model.tmdl`

- [ ] **Step 1: Write `model.tmdl`**

```tmdl
model Model
	culture: pt-BR
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: pt-BR
	dataAccessOptions
		fastCombine
		legacyRedirects
		returnErrorValuesAsNull

annotation PBI_ProTooling = ["DevMode"]

annotation PBI_QueryOrder = ["UrlBaseBCB","DataInicial","fnBcbSgs","d_indicador","f_indicadores","d_calendario","_Medidas"]

ref table d_indicador
ref table f_indicadores
ref table d_calendario
ref table _Medidas

ref cultureInfo pt-BR
```

- [ ] **Step 2: Verify all referenced table files exist**

Run:
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb/Panorama Macro BCB.SemanticModel/definition"
for t in d_indicador f_indicadores d_calendario _Medidas; do test -f "tables/$t.tmdl" && echo "$t OK" || echo "$t MISSING"; done
```
Expected: four `... OK` lines.

- [ ] **Step 3: Commit**

```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
git add "Panorama Macro BCB.SemanticModel/definition/model.tmdl"
git commit -m "feat: wire model tables and query order"
```

---

### Task 10: Report scaffold (platform, pbir, report.json, version, pages index)

**Files:**
- Create: `Panorama Macro BCB.Report/.platform`
- Create: `Panorama Macro BCB.Report/definition.pbir`
- Create: `Panorama Macro BCB.Report/definition/report.json`
- Create: `Panorama Macro BCB.Report/definition/version.json`
- Create: `Panorama Macro BCB.Report/definition/pages/pages.json`

- [ ] **Step 1: Create `.platform`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "Report",
    "displayName": "Panorama Macro BCB"
  },
  "config": {
    "version": "2.0",
    "logicalId": "b1a7e0c2-8000-4aaa-8bbb-000000000001"
  }
}
```

- [ ] **Step 2: Create `definition.pbir` (byPath — links to local model)**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byPath": {
      "path": "../Panorama Macro BCB.SemanticModel"
    }
  }
}
```

- [ ] **Step 3: Create `definition/version.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
  "version": "2.0.0"
}
```

- [ ] **Step 4: Create `definition/report.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
  "themeCollection": {
    "baseTheme": {
      "name": "CY25SU12",
      "type": "SharedResources"
    }
  },
  "resourcePackages": [
    {
      "name": "SharedResources",
      "type": "SharedResources",
      "items": [
        {
          "name": "CY25SU12",
          "path": "BaseThemes/CY25SU12.json",
          "type": "BaseTheme"
        }
      ]
    }
  ],
  "settings": {
    "useStylableVisualContainerHeader": true,
    "exportDataMode": "AllowSummarized",
    "defaultDrillFilterOtherVisuals": true,
    "useEnhancedTooltips": true
  }
}
```

- [ ] **Step 5: Create `definition/pages/pages.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
  "pageOrder": [
    "pagina01panorama",
    "pagina02explorar"
  ],
  "activePageName": "pagina01panorama"
}
```

- [ ] **Step 6: Verify JSON validity**

Run:
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
for f in "Panorama Macro BCB.Report/.platform" "Panorama Macro BCB.Report/definition.pbir" "Panorama Macro BCB.Report/definition/version.json" "Panorama Macro BCB.Report/definition/report.json" "Panorama Macro BCB.Report/definition/pages/pages.json"; do python -m json.tool "$f" > /dev/null || echo "BAD: $f"; done; echo done
```
Expected: `done` with no `BAD:` lines.

- [ ] **Step 7: Commit**

```bash
git add "Panorama Macro BCB.Report/.platform" "Panorama Macro BCB.Report/definition.pbir" "Panorama Macro BCB.Report/definition/version.json" "Panorama Macro BCB.Report/definition/report.json" "Panorama Macro BCB.Report/definition/pages/pages.json"
git commit -m "feat: add report scaffold and pages index"
```

---

### Task 11: Page 1 — "Panorama Macro" (title + 4 KPI cards + 4 mini line charts)

**Files:**
- Create: `Panorama Macro BCB.Report/definition/pages/pagina01panorama/page.json`
- Create: `Panorama Macro BCB.Report/definition/pages/pagina01panorama/visuals/v_titulo/visual.json`
- Create 4 KPI cards: `.../visuals/v_card_selic/visual.json`, `v_card_ipca/`, `v_card_dolar/`, `v_card_pib/`
- Create 4 mini line charts: `.../visuals/v_line_selic/visual.json`, `v_line_ipca/`, `v_line_dolar/`, `v_line_pib/`

- [ ] **Step 1: Create `page.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "pagina01panorama",
  "displayName": "Panorama Macro",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

- [ ] **Step 2: Create the title textbox `visuals/v_titulo/visual.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "v_titulo",
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
                  { "value": "Panorama Macroeconômico do Brasil", "textStyle": { "fontSize": "28px", "fontWeight": "bold", "color": "#0D4069" } }
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

- [ ] **Step 3: Create the 4 KPI cards from this template**

Template (replace the 4 tokens `@NAME@`, `@X@`, `@CODIGO@`, `@TITULO@` per the table below). Each card shows `Valor Atual`, filtered to one `codigo` via `filterConfig`.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "@NAME@",
  "position": { "x": @X@, "y": 110, "z": 1, "height": 140, "width": 290, "tabOrder": 1 },
  "visual": {
    "visualType": "cardVisual",
    "query": {
      "queryState": {
        "Data": {
          "projections": [
            {
              "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Valor Atual" } },
              "queryRef": "_Medidas.Valor Atual",
              "nativeQueryRef": "Valor Atual"
            }
          ]
        }
      }
    },
    "objects": {
      "value": [
        { "properties": { "fontSize": { "expr": { "Literal": { "Value": "36D" } } }, "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0D4069'" } } } } } } }
      ]
    },
    "visualContainerObjects": {
      "title": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } }, "text": { "expr": { "Literal": { "Value": "'@TITULO@'" } } }, "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#AC844C'" } } } } } } }
      ],
      "border": [ { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } ] }
    },
    "filterConfig": {
      "filters": [
        {
          "name": "f_@NAME@",
          "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_indicador" } }, "Property": "codigo" } },
          "type": "Categorical",
          "filter": {
            "Version": 2,
            "From": [ { "Name": "d", "Entity": "d_indicador", "Type": 0 } ],
            "Where": [
              { "Condition": { "In": { "Expressions": [ { "Column": { "Expression": { "SourceRef": { "Source": "d" } }, "Property": "codigo" } } ], "Values": [ [ { "Literal": { "Value": "'@CODIGO@'" } } ] ] } } }
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

Instances:

| folder            | @NAME@         | @X@ | @CODIGO@ | @TITULO@            |
|-------------------|----------------|-----|----------|---------------------|
| `v_card_selic`    | `v_card_selic` | 40  | `432`    | `Selic Meta (% a.a.)` |
| `v_card_ipca`     | `v_card_ipca`  | 350 | `13522`  | `IPCA 12m (%)`      |
| `v_card_dolar`    | `v_card_dolar` | 660 | `1`      | `Dólar PTAX (R$)`   |
| `v_card_pib`      | `v_card_pib`   | 970 | `4380`   | `PIB mensal (R$ mi)` |

- [ ] **Step 4: Create the 4 mini line charts from this template**

Template (tokens `@NAME@`, `@X@`, `@CODIGO@`). Line of `Valor Atual` over `d_calendario[mesano]`, filtered to one `codigo`.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "@NAME@",
  "position": { "x": @X@, "y": 270, "z": 2, "height": 420, "width": 290, "tabOrder": 2 },
  "visual": {
    "visualType": "lineChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_calendario" } }, "Property": "mesano" } }, "queryRef": "d_calendario.mesano", "nativeQueryRef": "mesano", "active": true }
          ]
        },
        "Y": {
          "projections": [
            { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Valor Atual" } }, "queryRef": "_Medidas.Valor Atual", "nativeQueryRef": "Valor Atual" }
          ]
        }
      }
    },
    "objects": {
      "categoryAxis": [ { "properties": { "showAxisTitle": { "expr": { "Literal": { "Value": "false" } } } } ],
      "valueAxis": [ { "properties": { "showAxisTitle": { "expr": { "Literal": { "Value": "false" } } } } ]
    },
    "filterConfig": {
      "filters": [
        {
          "name": "fl_@NAME@",
          "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_indicador" } }, "Property": "codigo" } },
          "type": "Categorical",
          "filter": {
            "Version": 2,
            "From": [ { "Name": "d", "Entity": "d_indicador", "Type": 0 } ],
            "Where": [
              { "Condition": { "In": { "Expressions": [ { "Column": { "Expression": { "SourceRef": { "Source": "d" } }, "Property": "codigo" } } ], "Values": [ [ { "Literal": { "Value": "'@CODIGO@'" } } ] ] } } }
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

Instances:

| folder          | @NAME@         | @X@ | @CODIGO@ |
|-----------------|----------------|-----|----------|
| `v_line_selic`  | `v_line_selic` | 40  | `432`    |
| `v_line_ipca`   | `v_line_ipca`  | 350 | `13522`  |
| `v_line_dolar`  | `v_line_dolar` | 660 | `1`      |
| `v_line_pib`    | `v_line_pib`   | 970 | `4380`   |

- [ ] **Step 5: Verify all page-1 JSON is valid**

Run:
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
find "Panorama Macro BCB.Report/definition/pages/pagina01panorama" -name "*.json" -print0 | while IFS= read -r -d '' f; do python -m json.tool "$f" > /dev/null || echo "BAD: $f"; done; echo done
```
Expected: `done` with no `BAD:` lines.

- [ ] **Step 6: Commit**

```bash
git add "Panorama Macro BCB.Report/definition/pages/pagina01panorama"
git commit -m "feat: add page 1 Panorama Macro with KPI cards and trend lines"
```

---

### Task 12: Page 2 — "Explorar Indicador" (slicer + line + 4 cards + table)

**Files:**
- Create: `Panorama Macro BCB.Report/definition/pages/pagina02explorar/page.json`
- Create: `.../visuals/v_slicer_ind/visual.json`
- Create: `.../visuals/v_line_geral/visual.json`
- Create: `.../visuals/v_card_atual/visual.json`, `v_card_var12/`, `v_card_max/`, `v_card_min/`
- Create: `.../visuals/v_tabela/visual.json`

- [ ] **Step 1: Create `page.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "pagina02explorar",
  "displayName": "Explorar Indicador",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

- [ ] **Step 2: Create the slicer `visuals/v_slicer_ind/visual.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "v_slicer_ind",
  "position": { "x": 40, "y": 40, "z": 0, "height": 80, "width": 400, "tabOrder": 0 },
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_indicador" } }, "Property": "indicador" } }, "queryRef": "d_indicador.indicador", "nativeQueryRef": "indicador", "active": true }
          ]
        }
      }
    },
    "objects": {
      "data": [ { "properties": { "mode": { "expr": { "Literal": { "Value": "'Dropdown'" } } } } ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 3: Create the main line chart `visuals/v_line_geral/visual.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "v_line_geral",
  "position": { "x": 40, "y": 140, "z": 1, "height": 420, "width": 800, "tabOrder": 1 },
  "visual": {
    "visualType": "lineChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_calendario" } }, "Property": "mesano" } }, "queryRef": "d_calendario.mesano", "nativeQueryRef": "mesano", "active": true }
          ]
        },
        "Y": {
          "projections": [
            { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Valor Atual" } }, "queryRef": "_Medidas.Valor Atual", "nativeQueryRef": "Valor Atual" }
          ]
        }
      }
    },
    "objects": {
      "lineStyles": [ { "properties": { "showMarker": { "expr": { "Literal": { "Value": "true" } } } } ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 4: Create the 4 stat cards from this template**

Template (tokens `@NAME@`, `@Y@`, `@MEASURE@`, `@TITULO@`). No per-card filter — they react to the slicer.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "@NAME@",
  "position": { "x": 870, "y": @Y@, "z": 2, "height": 100, "width": 370, "tabOrder": 2 },
  "visual": {
    "visualType": "cardVisual",
    "query": {
      "queryState": {
        "Data": {
          "projections": [
            { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "@MEASURE@" } }, "queryRef": "_Medidas.@MEASURE@", "nativeQueryRef": "@MEASURE@" }
          ]
        }
      }
    },
    "visualContainerObjects": {
      "title": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } }, "text": { "expr": { "Literal": { "Value": "'@TITULO@'" } } } } }
      ],
      "border": [ { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } ] }
    },
    "drillFilterOtherVisuals": true
  }
}
```

Instances:

| folder          | @NAME@         | @Y@ | @MEASURE@           | @TITULO@          |
|-----------------|----------------|-----|---------------------|-------------------|
| `v_card_atual`  | `v_card_atual` | 140 | `Valor Atual`       | `Valor Atual`     |
| `v_card_var12`  | `v_card_var12` | 250 | `Variação 12 Meses` | `Variação 12 Meses` |
| `v_card_max`    | `v_card_max`   | 360 | `Máximo`            | `Máximo`          |
| `v_card_min`    | `v_card_min`   | 470 | `Mínimo`            | `Mínimo`          |

- [ ] **Step 5: Create the table `visuals/v_tabela/visual.json`**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "v_tabela",
  "position": { "x": 40, "y": 580, "z": 3, "height": 120, "width": 800, "tabOrder": 3 },
  "visual": {
    "visualType": "tableEx",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "d_calendario" } }, "Property": "mesano" } }, "queryRef": "d_calendario.mesano", "nativeQueryRef": "mesano" },
            { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Valor Atual" } }, "queryRef": "_Medidas.Valor Atual", "nativeQueryRef": "Valor Atual" }
          ]
        }
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 6: Verify all page-2 JSON is valid**

Run:
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
find "Panorama Macro BCB.Report/definition/pages/pagina02explorar" -name "*.json" -print0 | while IFS= read -r -d '' f; do python -m json.tool "$f" > /dev/null || echo "BAD: $f"; done; echo done
```
Expected: `done` with no `BAD:` lines.

- [ ] **Step 7: Commit**

```bash
git add "Panorama Macro BCB.Report/definition/pages/pagina02explorar"
git commit -m "feat: add page 2 Explorar Indicador with slicer, line, cards and table"
```

---

### Task 13: README, final acceptance, push instructions

**Files:**
- Modify: `README.md` (replace skeleton with full content)

- [ ] **Step 1: Replace `README.md` with full content**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
git add README.md
git commit -m "docs: complete README with source, model and usage"
```

- [ ] **Step 3: Full repository JSON sanity sweep**

Run:
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
find . -path ./.git -prune -o -name "*.json" -print0 | while IFS= read -r -d '' f; do python -m json.tool "$f" > /dev/null || echo "BAD: $f"; done; echo "sweep done"
```
Expected: `sweep done` with no `BAD:` lines.

- [ ] **Step 4: MANUAL ACCEPTANCE (user, in Power BI Desktop)**

Open `Panorama Macro BCB.pbip`, set source privacy to Public, press Refresh.
Expected: `f_indicadores` loads all 7 series with history; both pages render with
cards and charts reacting to the selected indicator. This is the definitive test.

- [ ] **Step 5: Push to GitHub (requires the user's account)**

Preferred (if `gh` is authenticated):
```bash
cd "/c/Users/Fabiano Amaral/repos/pbi_panorama_macro_bcb"
gh repo create pbi_panorama_macro_bcb --public --source=. --remote=origin --push
```
Fallback (manual remote):
```bash
git remote add origin https://github.com/<user>/pbi_panorama_macro_bcb.git
git branch -M main
git push -u origin main
```

---

## Self-Review (author)

**Spec coverage:** §2 fonte → Task 3; §2 séries → Task 4; §3 star schema → Tasks 4–7;
§4 PBIP format → Tasks 2,9,10; §5 camada M / windowing → Task 3; §6 medidas → Task 8;
§7 report 2 páginas → Tasks 10–12; §8 README/gitignore/git/push → Tasks 1,13;
§9 fora de escopo respeitado (sem Focus/field params/RLS); §10 critérios → Task 13 Step 4.

**Placeholder scan:** the only `@TOKEN@` markers are explicit template variables with
resolution tables immediately below each; no TBD/TODO left.

**Type consistency:** measure names (`Valor Atual`, `Variação 12 Meses`, `Máximo`,
`Mínimo`), column names (`codigo`, `data`, `valor`, `mesano`, `indicador`) and entity
names (`_Medidas`, `d_indicador`, `f_indicadores`, `d_calendario`) match across model
and report tasks. `codigo` is text everywhere; card/line filters use `'value'` literals.
```
