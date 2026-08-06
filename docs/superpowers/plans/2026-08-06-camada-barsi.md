# Camada Barsi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evoluir o `pbi_panorama_financeiro` para apoiar a tomada de decisão pelo método Barsi — screener de preço-teto (Bazin), consistência de dividendos, score/ranking e simulador de renda passiva sobre um universo BESST ampliado da B3.

**Architecture:** Estender o star schema existente (`d_empresa`/`f_proventos`) com uma tabela de-para BESST, um fato anual agregado e tabelas what-if; concentrar a lógica Barsi em medidas DAX na tabela `_Medidas`. As fórmulas não-triviais (streak de anos consecutivos e bola de neve) são primeiro implementadas e testadas em um oráculo Python puro (`scripts/barsi_calc.py` + pytest); o DAX espelha essa lógica verificada.

**Tech Stack:** Power BI Desktop (PBIP/TMDL), Power Query (M), DAX, Python 3 (pytest, sem dependências externas no oráculo).

---

## Convenções e cuidados deste projeto (ler antes de começar)

- **`expressions.tmdl` tem `BrapiToken` REAL no working copy e está protegido por `git update-index --skip-worktree`.** NUNCA commitar o token. Para commitar mudança legítima nesse arquivo (Tarefa 2): `git update-index --no-skip-worktree "<arquivo>"` → zerar token (`BrapiToken = ""`) → `git add` → commit → `git update-index --skip-worktree "<arquivo>"`. Em clone novo, reaplicar o skip-worktree.
- **O Desktop reformata arquivos ao salvar** — sempre revisar `git diff` e commitar só o que a tarefa mudou (evitar ruído de reformatação e remoção de `filterConfig`).
- **Novas tabelas TMDL precisam de `ref table <nome>` em `model.tmdl`** — senão o Desktop não as carrega.
- **Medidas dedicadas com filtro embutido** (padrão `REMOVEFILTERS` + filtro em coluna) são preferidas a `filterConfig` no visual, porque o Desktop remove `filterConfig` ao salvar.
- Código/identificadores em inglês; textos de negócio (displayName, descrições) em pt-BR. Tema padrão do Power BI (sem marca — decisão do dono).

## File Structure

**Criar:**
- `scripts/barsi_calc.py` — oráculo puro-Python: mapeamento BESST, streak de anos consecutivos, cortes, CAGR, bola de neve. Fonte de verdade das fórmulas.
- `tests/test_barsi_calc.py` — testes pytest do oráculo.
- `Panorama Macro BCB.SemanticModel/definition/tables/d_besst.tmdl` — de-para ticker→BESST (inline M).
- `Panorama Macro BCB.SemanticModel/definition/tables/f_proventos_anual.tmdl` — fato anual (Group By em M).
- `Panorama Macro BCB.SemanticModel/definition/tables/p_YieldDesejado.tmdl` — what-if (0,04–0,10).
- `Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_AporteMensal.tmdl` — what-if.
- `Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_DYEsperado.tmdl` — what-if.
- `Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_CrescAporte.tmdl` — what-if (crescimento anual do aporte).
- `Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_Anos.tmdl` — what-if (horizonte).
- `Panorama Macro BCB.SemanticModel/definition/tables/d_horizonte.tmdl` — eixo 1..30 anos p/ curva do simulador.
- `Panorama Macro BCB.Report/definition/pages/pagina04detalhe/` — página Detalhe da Ação.
- `Panorama Macro BCB.Report/definition/pages/pagina05ranking/` — página Ranking Barsi.
- `Panorama Macro BCB.Report/definition/pages/pagina06simulador/` — página Simulador.
- `contracts/panorama/d_empresa.yml` e `contracts/panorama/f_proventos.yml` — atualizar/estender (ver Tarefa 15).
- `outputs/decisions/2026-08-06-camada-barsi.md` — registro de decisões.

**Modificar:**
- `.../definition/expressions.tmdl` — `fnYahooProventos` (range 10y) + `IbovTickers` (universo ampliado).
- `.../definition/tables/d_empresa.tmdl` — coluna `besst` + merge no partition M.
- `.../definition/tables/_Medidas.tmdl` — medidas Barsi/score/simulador.
- `.../definition/relationships.tmdl` — relação `f_proventos_anual`→`d_empresa`.
- `.../definition/model.tmdl` — `ref table` das novas tabelas + `PBI_QueryOrder`.
- `.../Report/definition/pages/pagina03dividendos/` — upgrade para Screener Barsi.
- `.../Report/definition/pages/pages.json` — incluir novas páginas.
- `scripts/dq_check_panorama.py` — validar `besst`, teto, janela 10a.
- `README.md`, `CLAUDE.md` — documentar novidades.

---

## Fase 0 — Oráculo Python (TDD)

### Task 1: Oráculo de cálculos Barsi + testes

**Files:**
- Create: `scripts/barsi_calc.py`
- Test: `tests/test_barsi_calc.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_barsi_calc.py`:

```python
"""Testes do oráculo Barsi. Fonte de verdade das fórmulas espelhadas em DAX."""
from scripts.barsi_calc import (
    besst_de_ticker,
    dividendo_medio_anual,
    preco_teto,
    anos_pagando,
    anos_consecutivos,
    cortes_dividendo,
    cagr_dividendo,
    score_barsi,
    patrimonio_projetado,
    renda_passiva_mensal,
)


def test_besst_por_override_de_ticker():
    assert besst_de_ticker("BBAS3", "Finanças e Seguros") == "B"
    assert besst_de_ticker("BBSE3", "Finanças e Seguros") == "SE"
    assert besst_de_ticker("SBSP3", "Utilidade Pública") == "SA"
    assert besst_de_ticker("EGIE3", "Utilidade Pública") == "E"


def test_besst_fallback_telecom_e_desconhecido():
    assert besst_de_ticker("NOVATELE3", "Telecomunicações") == "T"
    assert besst_de_ticker("XPTO3", "Consumo Cíclico") == "—"


def test_dividendo_medio_usa_denominador_fixo_de_5_anos():
    # paga 2 nos últimos 3 anos, nada antes -> média = (1+1+2)/5? não: soma/5
    por_ano = {2025: 1.0, 2024: 1.0, 2023: 2.0}
    # ano de referência 2026 -> considera 2021..2025; soma=4.0 -> /5 = 0.8
    assert dividendo_medio_anual(por_ano, ano_ref=2026) == 0.8


def test_preco_teto():
    assert preco_teto(div_medio=3.0, yield_desejado=0.06) == 50.0
    assert preco_teto(div_medio=0.0, yield_desejado=0.06) == 0.0


def test_anos_pagando_janela_10():
    por_ano = {y: 1.0 for y in range(2016, 2026)}  # 10 anos pagos
    por_ano[2020] = 0.0  # um ano sem pagar
    assert anos_pagando(por_ano, ano_ref=2026, janela=10) == 9


def test_anos_consecutivos_conta_ate_o_ultimo_ano_completo():
    por_ano = {2025: 1, 2024: 1, 2023: 1, 2021: 1, 2020: 1}  # 2022 faltando
    assert anos_consecutivos(por_ano, ano_ref=2026, janela=10) == 3


def test_anos_consecutivos_zero_se_ultimo_ano_nao_pagou():
    por_ano = {2024: 1, 2023: 1}
    assert anos_consecutivos(por_ano, ano_ref=2026, janela=10) == 0


def test_cortes_dividendo():
    por_ano = {2021: 1.0, 2022: 2.0, 2023: 1.5, 2024: 1.5, 2025: 3.0}
    # quedas: 2023 (<2022). -> 1 corte
    assert cortes_dividendo(por_ano, ano_ref=2026, janela=10) == 1


def test_cagr_dividendo():
    por_ano = {2020: 1.0, 2025: 2.0}  # ini 2020, fim 2025, 5 anos
    assert round(cagr_dividendo(por_ano, ano_ref=2026), 4) == round(2.0 ** (1 / 5) - 1, 4)


def test_score_limitado_entre_0_e_100():
    s = score_barsi(dy_medio=0.20, anos_consec=20, is_besst=True, margem=0.9, pl=5.0)
    assert s == 100.0
    s0 = score_barsi(dy_medio=0.0, anos_consec=0, is_besst=False, margem=-0.5, pl=-1.0)
    assert s0 == 0.0


def test_patrimonio_projetado_annuity_growing():
    # aporte anual 12000, d=0, g=0, 3 anos -> soma pura = 36000
    assert patrimonio_projetado(aporte_mensal=1000, dy=0.0, cresc_aporte=0.0, anos=3) == 36000.0


def test_renda_passiva_mensal():
    fv = patrimonio_projetado(aporte_mensal=1000, dy=0.06, cresc_aporte=0.0, anos=10)
    assert round(renda_passiva_mensal(fv, dy=0.06), 2) == round(fv * 0.06 / 12, 2)
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `python -m pytest tests/test_barsi_calc.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.barsi_calc'` (ou ImportError das funções).

> Se `pytest` não estiver instalado: `python -m pip install pytest`. Garanta um `__init__.py` vazio em `scripts/` e um `conftest.py` na raiz (ou rode com `python -m pytest` da raiz do projeto, que adiciona o cwd ao path).

- [ ] **Step 3: Implementar o oráculo**

Create `scripts/barsi_calc.py`:

```python
"""Oráculo puro-Python das fórmulas do método Barsi.

Fonte de verdade espelhada nas medidas DAX de _Medidas.tmdl. Sem dependências
externas para poder ser testado e importado pelo dq_check.
"""
from __future__ import annotations

# --- BESST -----------------------------------------------------------------
# Override por ticker (setor da brapi é ambíguo: "Finanças e Seguros" mistura
# banco e seguradora; "Utilidade Pública" mistura energia e saneamento).
BESST_OVERRIDE: dict[str, str] = {
    # Bancos
    "BBAS3": "B", "BBDC3": "B", "BBDC4": "B", "ITUB4": "B", "SANB11": "B",
    "BPAC11": "B", "ABCB4": "B", "BMGB4": "B", "ITSA4": "B",
    # Energia elétrica
    "CMIG4": "E", "CPFE3": "E", "CPLE6": "E", "EGIE3": "E", "ELET3": "E",
    "ELET6": "E", "ENGI11": "E", "ENEV3": "E", "EQTL3": "E", "TAEE11": "E",
    "ISAE4": "E", "AURE3": "E", "NEOE3": "E", "AESB3": "E", "ALUP11": "E",
    # Saneamento
    "SBSP3": "SA", "SAPR4": "SA", "SAPR11": "SA", "CSMG3": "SA", "ORVR3": "SA",
    # Seguros
    "BBSE3": "SE", "PSSA3": "SE", "CXSE3": "SE", "WIZC3": "SE", "IRBR3": "SE",
    # Telecom
    "VIVT3": "T", "TIMS3": "T", "DESK3": "T", "FIQE3": "T",
}

BESST_NOME: dict[str, str] = {
    "B": "Bancos", "E": "Energia", "SA": "Saneamento",
    "SE": "Seguros", "T": "Telecom", "—": "Fora BESST",
}


def besst_de_ticker(ticker: str, setor: str | None) -> str:
    """Resolve a sigla BESST: override por ticker; fallback Telecom por setor; senão '—'."""
    if ticker in BESST_OVERRIDE:
        return BESST_OVERRIDE[ticker]
    if setor == "Telecomunicações":
        return "T"
    return "—"


def is_besst(sigla: str) -> bool:
    return sigla in ("B", "E", "SA", "SE", "T")


# --- Preço-teto (Bazin) ----------------------------------------------------
def dividendo_medio_anual(por_ano: dict[int, float], ano_ref: int, janela: int = 5) -> float:
    """Soma dos proventos dos últimos `janela` anos completos / `janela`
    (denominador fixo penaliza anos sem pagamento)."""
    anos = range(ano_ref - janela, ano_ref)  # ex.: 2026 -> 2021..2025
    soma = sum(por_ano.get(a, 0.0) for a in anos)
    return soma / janela


def preco_teto(div_medio: float, yield_desejado: float) -> float:
    if yield_desejado <= 0:
        return 0.0
    return div_medio / yield_desejado


# --- Consistência ----------------------------------------------------------
def anos_pagando(por_ano: dict[int, float], ano_ref: int, janela: int = 10) -> int:
    anos = range(ano_ref - janela, ano_ref)
    return sum(1 for a in anos if por_ano.get(a, 0.0) > 0)


def anos_consecutivos(por_ano: dict[int, float], ano_ref: int, janela: int = 10) -> int:
    """Maior sequência terminando no último ano completo (ano_ref-1)."""
    ultimo = ano_ref - 1
    streak = 0
    for a in range(ultimo, ultimo - janela, -1):
        if por_ano.get(a, 0.0) > 0:
            streak += 1
        else:
            break
    return streak


def cortes_dividendo(por_ano: dict[int, float], ano_ref: int, janela: int = 10) -> int:
    ultimo = ano_ref - 1
    cortes = 0
    for a in range(ultimo - janela + 1, ultimo + 1):
        atual = por_ano.get(a, 0.0)
        ant = por_ano.get(a - 1, 0.0)
        if ant > 0 and atual < ant:
            cortes += 1
    return cortes


def cagr_dividendo(por_ano: dict[int, float], ano_ref: int, janela: int = 5) -> float:
    fim = ano_ref - 1
    ini = fim - janela
    v_fim = por_ano.get(fim, 0.0)
    v_ini = por_ano.get(ini, 0.0)
    if v_ini > 0 and v_fim > 0:
        return (v_fim / v_ini) ** (1 / janela) - 1
    return 0.0


# --- Score -----------------------------------------------------------------
def score_barsi(dy_medio: float, anos_consec: int, is_besst: bool,
                margem: float, pl: float) -> float:
    """0–100. Pesos: DY 30, consecutivos 25, BESST 15, margem 20, P/L 10."""
    s_dy = min(dy_medio / 0.12, 1.0) * 30
    s_consec = min(anos_consec / 10, 1.0) * 25
    s_besst = 15.0 if is_besst else 0.0
    s_margem = min(margem / 0.30, 1.0) * 20 if margem > 0 else 0.0
    s_pl = (20 - pl) / 20 * 10 if 0 < pl <= 20 else 0.0
    return round(s_dy + s_consec + s_besst + s_margem + s_pl, 2)


# --- Bola de neve ----------------------------------------------------------
def patrimonio_projetado(aporte_mensal: float, dy: float, cresc_aporte: float, anos: int) -> float:
    """FV de aportes anuais crescentes (g) reinvestidos a taxa `dy` (dividendos
    reinvestidos, sem ganho de capital). Aporte do ano t compõe por (anos-t)."""
    a_anual = aporte_mensal * 12
    total = 0.0
    for t in range(1, anos + 1):
        total += a_anual * (1 + cresc_aporte) ** (t - 1) * (1 + dy) ** (anos - t)
    return round(total, 2)


def renda_passiva_mensal(patrimonio: float, dy: float) -> float:
    return patrimonio * dy / 12
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python -m pytest tests/test_barsi_calc.py -v`
Expected: PASS — 11 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/barsi_calc.py tests/test_barsi_calc.py
git commit -m "feat(barsi): oraculo Python das formulas Barsi com testes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Fase 1 — Modelo: ingestão e tabelas

### Task 2: fnYahooProventos 10 anos + universo BESST ampliado

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/expressions.tmdl`

- [ ] **Step 1: Desproteger o arquivo (skip-worktree)**

Run: `git update-index --no-skip-worktree "Panorama Macro BCB.SemanticModel/definition/expressions.tmdl"`
Expected: sem saída (sucesso).

- [ ] **Step 2: Estender a janela do Yahoo para 10 anos**

Em `expressions.tmdl`, dentro de `fnYahooProventos`, trocar a `Query` de `range = "1y"` para `range = "10y"`:

```
                    Query = [range = "10y", interval = "1d", events = "div"],
```

- [ ] **Step 3: Ampliar `IbovTickers` com pagadoras BESST fora do Ibovespa**

Substituir o valor de `IbovTickers` (mantendo o nome do parâmetro para não quebrar as partições de `d_empresa`/`f_proventos`), acrescentando ao final: `ABCB4,BMGB4,NEOE3,AESB3,ALUP11,SAPR11,ORVR3,WIZC3,DESK3,FIQE3`. O valor final passa a ser:

```
expression IbovTickers = "ABEV3,ALOS3,ASAI3,AURE3,AZUL4,AZZA3,B3SA3,BBAS3,BBDC3,BBDC4,BBSE3,BEEF3,BPAC11,BRAP4,BRAV3,BRFS3,BRKM5,CMIG4,CMIN3,COGN3,CPFE3,CPLE6,CRFB3,CSAN3,CSNA3,CVCB3,CXSE3,CYRE3,EGIE3,ELET3,ELET6,EMBR3,ENGI11,ENEV3,EQTL3,FLRY3,GGBR4,GOAU4,HAPV3,HYPE3,IGTI11,IRBR3,ISAE4,ITSA4,ITUB4,KLBN11,LREN3,MGLU3,MRFG3,MRVE3,MULT3,NATU3,PCAR3,PETR3,PETR4,PETZ3,POMO4,PRIO3,PSSA3,RADL3,RAIL3,RAIZ4,RDOR3,RECV3,RENT3,SANB11,SBSP3,SLCE3,SMTO3,STBP3,SUZB3,TAEE11,TIMS3,TOTS3,UGPA3,USIM5,VALE3,VAMO3,VBBR3,VIVA3,VIVT3,WEGE3,YDUQ3,ALLD3,CSMG3,ODPV3,KEPL3,SAPR4,ABCB4,BMGB4,NEOE3,AESB3,ALUP11,SAPR11,ORVR3,WIZC3,DESK3,FIQE3" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

- [ ] **Step 4: Garantir token zerado antes de commitar**

Confirmar que `BrapiToken` está `""` no diff. Em `expressions.tmdl`, a linha deve ficar:

```
expression BrapiToken = "" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

Run: `git diff "Panorama Macro BCB.SemanticModel/definition/expressions.tmdl"`
Expected: mostra apenas (a) `range` 1y→10y, (b) novo valor de `IbovTickers`, (c) `BrapiToken` zerado. Nenhum token real presente.

- [ ] **Step 5: Commit e reativar proteção**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/expressions.tmdl"
git commit -m "feat(model): Yahoo 10 anos de proventos + universo BESST ampliado

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git update-index --skip-worktree "Panorama Macro BCB.SemanticModel/definition/expressions.tmdl"
```

> Após o commit, reabrir o Desktop e repreencher o `BrapiToken` localmente para atualizar (o skip-worktree impede que o valor local volte ao git).

### Task 3: Tabela de-para `d_besst`

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/d_besst.tmdl`

- [ ] **Step 1: Criar a tabela inline**

Create `d_besst.tmdl` (siglas idênticas ao `BESST_OVERRIDE` do oráculo):

```
table d_besst
	lineageTag: b1a7e0c2-a001-4aaa-8bbb-000000000001

	column ticker
		dataType: string
		lineageTag: b1a7e0c2-a001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: ticker

		annotation SummarizationSetBy = Automatic

	column besst_sigla
		dataType: string
		lineageTag: b1a7e0c2-a001-4aaa-8bbb-000000000003
		summarizeBy: none
		sourceColumn: besst_sigla

		annotation SummarizationSetBy = Automatic

	column besst_nome
		dataType: string
		lineageTag: b1a7e0c2-a001-4aaa-8bbb-000000000004
		summarizeBy: none
		sourceColumn: besst_nome

		annotation SummarizationSetBy = Automatic

	partition d_besst = m
		mode: import
		source =
				let
				    linhas = {
				        [ticker="BBAS3", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="BBDC3", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="BBDC4", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="ITUB4", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="SANB11", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="BPAC11", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="ABCB4", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="BMGB4", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="ITSA4", besst_sigla="B", besst_nome="Bancos"],
				        [ticker="CMIG4", besst_sigla="E", besst_nome="Energia"],
				        [ticker="CPFE3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="CPLE6", besst_sigla="E", besst_nome="Energia"],
				        [ticker="EGIE3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="ELET3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="ELET6", besst_sigla="E", besst_nome="Energia"],
				        [ticker="ENGI11", besst_sigla="E", besst_nome="Energia"],
				        [ticker="ENEV3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="EQTL3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="TAEE11", besst_sigla="E", besst_nome="Energia"],
				        [ticker="ISAE4", besst_sigla="E", besst_nome="Energia"],
				        [ticker="AURE3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="NEOE3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="AESB3", besst_sigla="E", besst_nome="Energia"],
				        [ticker="ALUP11", besst_sigla="E", besst_nome="Energia"],
				        [ticker="SBSP3", besst_sigla="SA", besst_nome="Saneamento"],
				        [ticker="SAPR4", besst_sigla="SA", besst_nome="Saneamento"],
				        [ticker="SAPR11", besst_sigla="SA", besst_nome="Saneamento"],
				        [ticker="CSMG3", besst_sigla="SA", besst_nome="Saneamento"],
				        [ticker="ORVR3", besst_sigla="SA", besst_nome="Saneamento"],
				        [ticker="BBSE3", besst_sigla="SE", besst_nome="Seguros"],
				        [ticker="PSSA3", besst_sigla="SE", besst_nome="Seguros"],
				        [ticker="CXSE3", besst_sigla="SE", besst_nome="Seguros"],
				        [ticker="WIZC3", besst_sigla="SE", besst_nome="Seguros"],
				        [ticker="IRBR3", besst_sigla="SE", besst_nome="Seguros"],
				        [ticker="VIVT3", besst_sigla="T", besst_nome="Telecom"],
				        [ticker="TIMS3", besst_sigla="T", besst_nome="Telecom"],
				        [ticker="DESK3", besst_sigla="T", besst_nome="Telecom"],
				        [ticker="FIQE3", besst_sigla="T", besst_nome="Telecom"]
				    },
				    t = Table.FromRecords(linhas),
				    tipos = Table.TransformColumnTypes(t, {{"ticker", type text}, {"besst_sigla", type text}, {"besst_nome", type text}})
				in
				    tipos

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Validar sintaxe/estrutura**

Run: `python -c "import pathlib; t=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/d_besst.tmdl').read_text(encoding='utf-8'); assert t.count('besst_sigla')>=3 and 'partition d_besst = m' in t; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/d_besst.tmdl"
git commit -m "feat(model): tabela de-para d_besst (ticker->BESST)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 4: Coluna `besst` em `d_empresa`

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/tables/d_empresa.tmdl`

- [ ] **Step 1: Adicionar a definição da coluna `besst`**

Em `d_empresa.tmdl`, logo após o bloco `column setor` (antes de `column preco_atual`), inserir:

```
	column besst
		dataType: string
		lineageTag: b1a7e0c2-8001-4aaa-8bbb-000000000009
		summarizeBy: none
		sourceColumn: besst

		annotation SummarizationSetBy = Automatic
```

- [ ] **Step 2: Resolver `besst` no partition M (merge + fallback)**

No partition M de `d_empresa`, substituir o passo final `ordem = Table.SelectColumns(tipos, {...})` e o `in ordem` por:

```
				    ordem = Table.SelectColumns(tipos, {"ticker", "nome", "setor", "preco_atual", "pl", "min_52s", "max_52s"}),
				    comBesst = Table.NestedJoin(ordem, {"ticker"}, d_besst, {"ticker"}, "b", JoinKind.LeftOuter),
				    expBesst = Table.ExpandTableColumn(comBesst, "b", {"besst_sigla"}, {"besst_sigla"}),
				    resolveBesst = Table.AddColumn(expBesst, "besst", each
				        if [besst_sigla] <> null then [besst_sigla]
				        else if [setor] = "Telecomunicações" then "T"
				        else "—", type text),
				    ordemFinal = Table.SelectColumns(resolveBesst, {"ticker", "nome", "setor", "besst", "preco_atual", "pl", "min_52s", "max_52s"})
				in
				    ordemFinal
```

- [ ] **Step 3: Validar estrutura**

Run: `python -c "import pathlib; t=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/d_empresa.tmdl').read_text(encoding='utf-8'); assert 'column besst' in t and 'd_besst' in t and 'ordemFinal' in t; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/d_empresa.tmdl"
git commit -m "feat(model): coluna besst em d_empresa (merge d_besst + fallback telecom)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 5: Fato anual `f_proventos_anual`

**Files:**
- Create: `Panorama Macro BCB.SemanticModel/definition/tables/f_proventos_anual.tmdl`

- [ ] **Step 1: Criar a tabela (Group By em M)**

Create `f_proventos_anual.tmdl`:

```
table f_proventos_anual
	lineageTag: b1a7e0c2-b001-4aaa-8bbb-000000000001

	column ticker
		dataType: string
		lineageTag: b1a7e0c2-b001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: ticker

		annotation SummarizationSetBy = Automatic

	column ano
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-b001-4aaa-8bbb-000000000003
		summarizeBy: none
		sourceColumn: ano

		annotation SummarizationSetBy = Automatic

	column total_proventos
		dataType: double
		formatString: #,0.00
		lineageTag: b1a7e0c2-b001-4aaa-8bbb-000000000004
		summarizeBy: sum
		sourceColumn: total_proventos

		annotation SummarizationSetBy = Automatic

	partition f_proventos_anual = m
		mode: import
		source =
				let
				    Fonte = f_proventos,
				    ComAno = Table.AddColumn(Fonte, "ano", each Date.Year([data_pagamento]), Int64.Type),
				    Agrupado = Table.Group(ComAno, {"ticker", "ano"}, {{"total_proventos", each List.Sum([valor]), type number}})
				in
				    Agrupado

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Validar estrutura**

Run: `python -c "import pathlib; t=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/f_proventos_anual.tmdl').read_text(encoding='utf-8'); assert 'Table.Group' in t and 'total_proventos' in t; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/f_proventos_anual.tmdl"
git commit -m "feat(model): fato anual f_proventos_anual (grao ticker/ano)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 6: Tabelas what-if e eixo do simulador

**Files:**
- Create: `p_YieldDesejado.tmdl`, `p_Sim_AporteMensal.tmdl`, `p_Sim_DYEsperado.tmdl`, `p_Sim_CrescAporte.tmdl`, `p_Sim_Anos.tmdl`, `d_horizonte.tmdl` (todas em `.../definition/tables/`)

- [ ] **Step 1: Criar `p_YieldDesejado.tmdl`**

```
table p_YieldDesejado
	lineageTag: b1a7e0c2-c001-4aaa-8bbb-000000000001

	column Valor
		dataType: double
		formatString: 0.0%
		lineageTag: b1a7e0c2-c001-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: [Value]

		annotation SummarizationSetBy = Automatic

	partition p_YieldDesejado = calculated
		mode: import
		source = GENERATESERIES(0.04, 0.1, 0.005)

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Criar `p_Sim_AporteMensal.tmdl`**

```
table p_Sim_AporteMensal
	lineageTag: b1a7e0c2-c002-4aaa-8bbb-000000000001

	column Valor
		dataType: int64
		formatString: #,0
		lineageTag: b1a7e0c2-c002-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: [Value]

		annotation SummarizationSetBy = Automatic

	partition p_Sim_AporteMensal = calculated
		mode: import
		source = GENERATESERIES(100, 20000, 100)

	annotation PBI_ResultType = Table
```

- [ ] **Step 3: Criar `p_Sim_DYEsperado.tmdl`**

```
table p_Sim_DYEsperado
	lineageTag: b1a7e0c2-c003-4aaa-8bbb-000000000001

	column Valor
		dataType: double
		formatString: 0.0%
		lineageTag: b1a7e0c2-c003-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: [Value]

		annotation SummarizationSetBy = Automatic

	partition p_Sim_DYEsperado = calculated
		mode: import
		source = GENERATESERIES(0.03, 0.12, 0.005)

	annotation PBI_ResultType = Table
```

- [ ] **Step 4: Criar `p_Sim_CrescAporte.tmdl`**

```
table p_Sim_CrescAporte
	lineageTag: b1a7e0c2-c004-4aaa-8bbb-000000000001

	column Valor
		dataType: double
		formatString: 0.0%
		lineageTag: b1a7e0c2-c004-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: [Value]

		annotation SummarizationSetBy = Automatic

	partition p_Sim_CrescAporte = calculated
		mode: import
		source = GENERATESERIES(0, 0.15, 0.01)

	annotation PBI_ResultType = Table
```

- [ ] **Step 5: Criar `p_Sim_Anos.tmdl`**

```
table p_Sim_Anos
	lineageTag: b1a7e0c2-c005-4aaa-8bbb-000000000001

	column Valor
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-c005-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: [Value]

		annotation SummarizationSetBy = Automatic

	partition p_Sim_Anos = calculated
		mode: import
		source = GENERATESERIES(1, 40, 1)

	annotation PBI_ResultType = Table
```

- [ ] **Step 6: Criar `d_horizonte.tmdl` (eixo da curva)**

```
table d_horizonte
	lineageTag: b1a7e0c2-c006-4aaa-8bbb-000000000001

	column ano
		dataType: int64
		formatString: 0
		lineageTag: b1a7e0c2-c006-4aaa-8bbb-000000000002
		summarizeBy: none
		sourceColumn: [Value]

		annotation SummarizationSetBy = Automatic

	partition d_horizonte = calculated
		mode: import
		source = GENERATESERIES(1, 40, 1)

	annotation PBI_ResultType = Table
```

- [ ] **Step 7: Validar estrutura das 6 tabelas**

Run: `python -c "import pathlib,glob; [print(f, 'ok') for f in ['p_YieldDesejado','p_Sim_AporteMensal','p_Sim_DYEsperado','p_Sim_CrescAporte','p_Sim_Anos','d_horizonte'] if 'GENERATESERIES' in pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/'+f+'.tmdl').read_text(encoding='utf-8')]"`
Expected: 6 linhas `... ok`

- [ ] **Step 8: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/p_YieldDesejado.tmdl" "Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_AporteMensal.tmdl" "Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_DYEsperado.tmdl" "Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_CrescAporte.tmdl" "Panorama Macro BCB.SemanticModel/definition/tables/p_Sim_Anos.tmdl" "Panorama Macro BCB.SemanticModel/definition/tables/d_horizonte.tmdl"
git commit -m "feat(model): tabelas what-if (yield, simulador) e eixo d_horizonte

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 7: Registrar tabelas em `model.tmdl` e relação nova

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/model.tmdl`
- Modify: `Panorama Macro BCB.SemanticModel/definition/relationships.tmdl`

- [ ] **Step 1: Adicionar `ref table` das novas tabelas**

Em `model.tmdl`, após `ref table f_proventos`, acrescentar:

```
ref table d_besst
ref table f_proventos_anual
ref table p_YieldDesejado
ref table p_Sim_AporteMensal
ref table p_Sim_DYEsperado
ref table p_Sim_CrescAporte
ref table p_Sim_Anos
ref table d_horizonte
```

- [ ] **Step 2: Atualizar `PBI_QueryOrder`**

Substituir a annotation `PBI_QueryOrder` por (acrescenta as novas queries de import; tabelas calculadas what-if não precisam constar, mas incluir `d_besst` e `f_proventos_anual`):

```
annotation PBI_QueryOrder = ["UrlBaseBCB","DataInicial","fnBcbSgs","UrlBaseBrapi","BrapiToken","IbovTickers","UrlBaseYahoo","fnYahooProventos","fnBrapiQuote","d_indicador","f_indicadores","d_calendario","d_empresa","d_besst","f_proventos","f_proventos_anual","_Medidas"]
```

- [ ] **Step 3: Adicionar a relação `f_proventos_anual` → `d_empresa`**

Em `relationships.tmdl`, acrescentar ao final:

```
relationship b1a7e0c2-6001-4aaa-8bbb-000000000005
	fromColumn: f_proventos_anual.ticker
	toColumn: d_empresa.ticker
```

- [ ] **Step 4: Validar**

Run: `python -c "import pathlib; m=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/model.tmdl').read_text(encoding='utf-8'); r=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/relationships.tmdl').read_text(encoding='utf-8'); assert 'ref table d_besst' in m and 'ref table d_horizonte' in m and 'f_proventos_anual.ticker' in r; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/model.tmdl" "Panorama Macro BCB.SemanticModel/definition/relationships.tmdl"
git commit -m "feat(model): registrar tabelas Barsi e relacao f_proventos_anual->d_empresa

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Fase 2 — Medidas DAX

### Task 8: Medidas de preço-teto (Bazin)

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl`

- [ ] **Step 1: Adicionar as medidas de teto**

Em `_Medidas.tmdl`, antes do bloco `column 'Coluna 1'`, inserir (pasta `08. Barsi`):

```
	measure 'Yield Desejado' = SELECTEDVALUE(p_YieldDesejado[Valor], 0.06)
		formatString: 0.0%
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000101

	/// Soma dos proventos dos últimos 5 anos completos ÷ 5 (denominador fixo penaliza anos sem pagamento).
	measure 'Dividendo Médio Anual 5a' =
			VAR _anoRef = YEAR(TODAY())
			VAR _soma =
			    CALCULATE(
			        SUM(f_proventos_anual[total_proventos]),
			        f_proventos_anual[ano] >= _anoRef - 5,
			        f_proventos_anual[ano] <= _anoRef - 1
			    )
			RETURN
			    DIVIDE(_soma, 5)
		formatString: #,0.00
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000102

	measure 'Preço-Teto' = DIVIDE([Dividendo Médio Anual 5a], [Yield Desejado])
		formatString: #,0.00
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000103

	/// Positivo = preço atual abaixo do teto (margem de segurança para comprar).
	measure 'Margem vs Teto %' = DIVIDE([Preço-Teto] - [Preço Atual Ação], [Preço Atual Ação])
		formatString: 0.0%
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000104

	measure 'DY Médio 5a' = DIVIDE([Dividendo Médio Anual 5a], [Preço Atual Ação])
		formatString: 0.00%
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000105

	measure 'Sinal Barsi' =
			VAR _preco = [Preço Atual Ação]
			VAR _teto = [Preço-Teto]
			RETURN
			    SWITCH(
			        TRUE(),
			        _teto = 0 || ISBLANK(_teto), "Sem histórico",
			        _preco <= _teto, "Comprar",
			        "Aguardar"
			    )
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000106

	/// 1 = comprar (preço ≤ teto). Para formatação condicional.
	measure 'Sinal Barsi (cor)' =
			VAR _preco = [Preço Atual Ação]
			VAR _teto = [Preço-Teto]
			RETURN
			    IF(_teto > 0 && _preco <= _teto, 1, 0)
		formatString: 0
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000107

	/// Nº de ações do universo filtrado com preço ≤ teto.
	measure 'Ações Abaixo do Teto' =
			COUNTROWS(
			    FILTER(
			        VALUES(d_empresa[ticker]),
			        [Preço Atual Ação] <= [Preço-Teto] && [Preço-Teto] > 0
			    )
			)
		formatString: 0
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000108
```

- [ ] **Step 2: Validar estrutura**

Run: `python -c "import pathlib; t=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl').read_text(encoding='utf-8'); [t.index(m) for m in ['Preço-Teto','Margem vs Teto %','Sinal Barsi','Yield Desejado']]; print('ok')"`
Expected: `ok` (todas as medidas presentes).

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl"
git commit -m "feat(dax): medidas de preco-teto Bazin (08. Barsi)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 9: Medidas de consistência

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl`

- [ ] **Step 1: Adicionar as medidas de consistência** (espelham `barsi_calc.py`; janela 10a)

Inserir junto às demais (pasta `08. Barsi`):

```
	measure 'Anos Pagando 10a' =
			VAR _anoRef = YEAR(TODAY())
			RETURN
			    CALCULATE(
			        DISTINCTCOUNT(f_proventos_anual[ano]),
			        f_proventos_anual[ano] >= _anoRef - 10,
			        f_proventos_anual[ano] <= _anoRef - 1,
			        f_proventos_anual[total_proventos] > 0
			    )
		formatString: 0
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000109

	/// Maior sequência de anos pagando terminando no último ano completo (janela 10a).
	measure 'Anos Consecutivos' =
			VAR _anoUltimo = YEAR(TODAY()) - 1
			VAR _janela = 10
			VAR _tab =
			    ADDCOLUMNS(
			        GENERATESERIES(_anoUltimo - _janela + 1, _anoUltimo, 1),
			        "@ano", [Value],
			        "@pago",
			            VAR _a = [Value]
			            RETURN CALCULATE(SUM(f_proventos_anual[total_proventos]), f_proventos_anual[ano] = _a)
			    )
			VAR _ultimoNaoPago = MAXX(FILTER(_tab, [@pago] = 0 || ISBLANK([@pago])), [@ano])
			RETURN
			    IF(ISBLANK(_ultimoNaoPago), _janela, _anoUltimo - _ultimoNaoPago)
		formatString: 0
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000110

	measure 'Cortes de Dividendo 10a' =
			VAR _anoUltimo = YEAR(TODAY()) - 1
			VAR _janela = 10
			VAR _tab =
			    ADDCOLUMNS(
			        GENERATESERIES(_anoUltimo - _janela + 1, _anoUltimo, 1),
			        "@ano", [Value],
			        "@val", VAR _a = [Value] RETURN CALCULATE(SUM(f_proventos_anual[total_proventos]), f_proventos_anual[ano] = _a)
			    )
			VAR _comAnt =
			    ADDCOLUMNS(_tab, "@ant", VAR _a = [@ano] RETURN MAXX(FILTER(_tab, [@ano] = _a - 1), [@val]))
			RETURN
			    COUNTROWS(FILTER(_comAnt, NOT ISBLANK([@ant]) && [@ant] > 0 && [@val] < [@ant]))
		formatString: 0
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000111

	measure 'Crescimento Dividendo CAGR 5a' =
			VAR _fim = YEAR(TODAY()) - 1
			VAR _ini = _fim - 5
			VAR _vFim = CALCULATE(SUM(f_proventos_anual[total_proventos]), f_proventos_anual[ano] = _fim)
			VAR _vIni = CALCULATE(SUM(f_proventos_anual[total_proventos]), f_proventos_anual[ano] = _ini)
			RETURN
			    IF(_vIni > 0 && _vFim > 0, (_vFim / _vIni) ^ (1 / 5) - 1)
		formatString: 0.0%
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000112
```

- [ ] **Step 2: Validar estrutura**

Run: `python -c "import pathlib; t=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl').read_text(encoding='utf-8'); [t.index(m) for m in ['Anos Pagando 10a','Anos Consecutivos','Cortes de Dividendo 10a','Crescimento Dividendo CAGR 5a']]; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl"
git commit -m "feat(dax): medidas de consistencia de dividendos (10a)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 10: Medida de Score Barsi

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl`

- [ ] **Step 1: Adicionar `Score Barsi`** (pesos idênticos a `score_barsi` do oráculo)

```
	/// Score 0–100. Pesos: DY Médio 5a 30 · Anos Consecutivos 25 · BESST 15 · Margem vs Teto 20 · P/L 10.
	measure 'Score Barsi' =
			VAR _dy = MIN(DIVIDE([DY Médio 5a], 0.12), 1) * 30
			VAR _consec = MIN(DIVIDE([Anos Consecutivos], 10), 1) * 25
			VAR _sigla = SELECTEDVALUE(d_empresa[besst])
			VAR _besst = IF(_sigla <> "—" && NOT ISBLANK(_sigla), 15, 0)
			VAR _m = [Margem vs Teto %]
			VAR _margem = IF(_m > 0, MIN(DIVIDE(_m, 0.30), 1) * 20, 0)
			VAR _p = [P/L]
			VAR _pl = IF(_p > 0 && _p <= 20, DIVIDE(20 - _p, 20) * 10, 0)
			RETURN
			    _dy + _consec + _besst + _margem + _pl
		formatString: #,0.0
		displayFolder: 08. Barsi
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000113
```

- [ ] **Step 2: Validar**

Run: `python -c "import pathlib; assert 'Score Barsi' in pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl').read_text(encoding='utf-8'); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl"
git commit -m "feat(dax): medida Score Barsi (pesos documentados)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 11: Medidas do simulador (bola de neve)

**Files:**
- Modify: `Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl`

- [ ] **Step 1: Adicionar as medidas do simulador** (pasta `09. Simulador`; espelham `patrimonio_projetado`)

```
	measure 'Sim Aporte Mensal' = SELECTEDVALUE(p_Sim_AporteMensal[Valor], 1000)
		formatString: #,0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000114

	measure 'Sim DY Esperado' = SELECTEDVALUE(p_Sim_DYEsperado[Valor], 0.06)
		formatString: 0.0%
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000115

	measure 'Sim Crescimento Aporte' = SELECTEDVALUE(p_Sim_CrescAporte[Valor], 0.05)
		formatString: 0.0%
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000116

	measure 'Sim Anos' = SELECTEDVALUE(p_Sim_Anos[Valor], 20)
		formatString: 0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000117

	/// FV de aportes anuais crescentes (g) reinvestidos ao yield (d), sem ganho de capital.
	measure 'Patrimônio Projetado' =
			VAR _A = [Sim Aporte Mensal] * 12
			VAR _d = [Sim DY Esperado]
			VAR _g = [Sim Crescimento Aporte]
			VAR _N = [Sim Anos]
			RETURN
			    SUMX(
			        GENERATESERIES(1, _N, 1),
			        VAR _t = [Value]
			        RETURN _A * (1 + _g) ^ (_t - 1) * (1 + _d) ^ (_N - _t)
			    )
		formatString: "R$ "#,0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000118

	measure 'Renda Passiva Mensal Projetada' = DIVIDE([Patrimônio Projetado] * [Sim DY Esperado], 12)
		formatString: "R$ "#,0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000119

	measure 'Total Aportado' =
			VAR _A = [Sim Aporte Mensal] * 12
			VAR _g = [Sim Crescimento Aporte]
			VAR _N = [Sim Anos]
			RETURN
			    SUMX(GENERATESERIES(1, _N, 1), _A * (1 + _g) ^ ([Value] - 1))
		formatString: "R$ "#,0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000120

	measure 'Dividendos Reinvestidos' = [Patrimônio Projetado] - [Total Aportado]
		formatString: "R$ "#,0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000121

	/// Patrimônio acumulado até o ano do eixo (d_horizonte[ano]); em branco além do horizonte selecionado.
	measure 'Patrimônio até o Ano' =
			VAR _A = [Sim Aporte Mensal] * 12
			VAR _d = [Sim DY Esperado]
			VAR _g = [Sim Crescimento Aporte]
			VAR _k = SELECTEDVALUE(d_horizonte[ano])
			RETURN
			    IF(
			        _k <= [Sim Anos],
			        SUMX(
			            GENERATESERIES(1, _k, 1),
			            VAR _t = [Value]
			            RETURN _A * (1 + _g) ^ (_t - 1) * (1 + _d) ^ (_k - _t)
			        )
			    )
		formatString: "R$ "#,0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000122

	measure 'Renda Mensal até o Ano' = DIVIDE([Patrimônio até o Ano] * [Sim DY Esperado], 12)
		formatString: "R$ "#,0
		displayFolder: 09. Simulador
		lineageTag: b1a7e0c2-7001-4aaa-8bbb-000000000123
```

- [ ] **Step 2: Validar**

Run: `python -c "import pathlib; t=pathlib.Path('Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl').read_text(encoding='utf-8'); [t.index(m) for m in ['Patrimônio Projetado','Renda Passiva Mensal Projetada','Patrimônio até o Ano']]; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add "Panorama Macro BCB.SemanticModel/definition/tables/_Medidas.tmdl"
git commit -m "feat(dax): medidas do simulador de renda passiva (bola de neve)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Fase 3 — Relatório

> Padrão PBIR: cada visual é uma pasta com `visual.json`; cada página tem `page.json`; a ordem fica em `pages.json`. Reusar o schema já visto em `pagina03dividendos`. Posições em coordenadas de 1280×720. Preferir bindings de medida/coluna via `projections` (evitar `filterConfig`, que o Desktop remove).

### Task 12: Upgrade da página 03 para "Seleção Barsi (Screener)"

**Files:**
- Modify: `.../Report/definition/pages/pagina03dividendos/page.json`
- Modify: `.../Report/definition/pages/pagina03dividendos/visuals/v_tabela_dy/visual.json`
- Modify: `.../Report/definition/pages/pagina03dividendos/visuals/v_slicer_setor/visual.json`
- Create: `.../pagina03dividendos/visuals/v_slicer_yield/visual.json`
- Create: `.../pagina03dividendos/visuals/v_card_abaixo_teto/visual.json`

- [ ] **Step 1: Renomear a página**

Em `pagina03dividendos/page.json`, trocar `displayName`:

```json
  "displayName": "Seleção Barsi",
```

- [ ] **Step 2: Reprojetar a tabela do screener**

Substituir o array `projections` de `v_tabela_dy/visual.json` por (Empresa · BESST · Preço · Preço-Teto · Margem vs Teto % · Sinal · DY 12m · DY 5a · Anos Consec. · P/L · Score). Cada item segue o padrão já existente (`Column` para colunas de `d_empresa`, `Measure` para `_Medidas`):

```json
"projections": [
  {"field": {"Column": {"Expression": {"SourceRef": {"Entity": "d_empresa"}}, "Property": "nome"}}, "queryRef": "d_empresa.nome", "nativeQueryRef": "nome"},
  {"field": {"Column": {"Expression": {"SourceRef": {"Entity": "d_empresa"}}, "Property": "besst"}}, "queryRef": "d_empresa.besst", "nativeQueryRef": "besst"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Preço Atual Ação"}}, "queryRef": "_Medidas.Preço Atual Ação", "nativeQueryRef": "Preço Atual Ação"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Preço-Teto"}}, "queryRef": "_Medidas.Preço-Teto", "nativeQueryRef": "Preço-Teto"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Margem vs Teto %"}}, "queryRef": "_Medidas.Margem vs Teto %", "nativeQueryRef": "Margem vs Teto %"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Sinal Barsi"}}, "queryRef": "_Medidas.Sinal Barsi", "nativeQueryRef": "Sinal Barsi"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Dividend Yield 12m"}}, "queryRef": "_Medidas.Dividend Yield 12m", "nativeQueryRef": "Dividend Yield 12m"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "DY Médio 5a"}}, "queryRef": "_Medidas.DY Médio 5a", "nativeQueryRef": "DY Médio 5a"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Anos Consecutivos"}}, "queryRef": "_Medidas.Anos Consecutivos", "nativeQueryRef": "Anos Consecutivos"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "P/L"}}, "queryRef": "_Medidas.P/L", "nativeQueryRef": "P/L"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Score Barsi"}}, "queryRef": "_Medidas.Score Barsi", "nativeQueryRef": "Score Barsi"}
]
```

Trocar também o `sortDefinition` para ordenar por `Score Barsi` `Descending` (mesma estrutura do sort atual, trocando `Property` para `Score Barsi`). Remover o bloco `filterConfig` inteiro deste visual (as colunas agora vêm por projeção; o Desktop não deve reintroduzir filtros).

- [ ] **Step 3: Trocar o slicer de setor para BESST**

Em `v_slicer_setor/visual.json`, trocar as duas ocorrências de `"Property": "setor"` por `"Property": "besst"` e os `queryRef`/`nativeQueryRef` de `setor` para `besst` (na `projection` e no `filterConfig`).

- [ ] **Step 4: Criar o slicer de Yield Desejado (what-if)**

Create `.../pagina03dividendos/visuals/v_slicer_yield/visual.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "v_slicer_yield",
  "position": { "x": 40, "y": 100, "z": 3000, "height": 90, "width": 300, "tabOrder": 3000 },
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "p_YieldDesejado" } }, "Property": "Valor" } }, "queryRef": "p_YieldDesejado.Valor", "nativeQueryRef": "Valor", "active": true }
          ]
        }
      }
    },
    "objects": { "data": [ { "properties": { "mode": { "expr": { "Literal": { "Value": "'Single'" } } } } } ] },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 5: Criar o card "Ações Abaixo do Teto"**

Create `.../pagina03dividendos/visuals/v_card_abaixo_teto/visual.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "v_card_abaixo_teto",
  "position": { "x": 40, "y": 200, "z": 3100, "height": 120, "width": 300, "tabOrder": 3100 },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Ações Abaixo do Teto" } }, "queryRef": "_Medidas.Ações Abaixo do Teto", "nativeQueryRef": "Ações Abaixo do Teto" }
          ]
        }
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 6: Validar JSON**

Run: `python -c "import json,glob; [json.load(open(f,encoding='utf-8')) for f in glob.glob('Panorama Macro BCB.Report/definition/pages/pagina03dividendos/**/*.json', recursive=True)]; print('json ok')"`
Expected: `json ok`

- [ ] **Step 7: Commit**

```bash
git add "Panorama Macro BCB.Report/definition/pages/pagina03dividendos"
git commit -m "feat(report): pagina 03 vira Selecao Barsi (screener preco-teto/score)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 13: Páginas Detalhe da Ação, Ranking e Simulador

**Files:**
- Create: `.../pages/pagina04detalhe/page.json` + visuais
- Create: `.../pages/pagina05ranking/page.json` + visuais
- Create: `.../pages/pagina06simulador/page.json` + visuais
- Modify: `.../pages/pages.json`

> Cada `visual.json` segue exatamente o padrão da Tarefa 12 (bloco `visual` com `visualType` + `query.queryState.Values.projections`). Abaixo, o `page.json` de cada página e a lista de visuais com seus bindings. Criar um arquivo `visuals/<nome>/visual.json` por item, copiando o template e trocando `name`, `position`, `visualType` e as `projections`.

- [ ] **Step 1: Página 04 — Detalhe da Ação**

Create `pagina04detalhe/page.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "pagina04detalhe",
  "displayName": "Detalhe da Ação",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

Visuais (criar cada um como `visuals/<name>/visual.json`):

| name | visualType | position (x,y,w,h) | projections (Entity.Property) |
|---|---|---|---|
| `v_slicer_ticker` | `slicer` | 40,60,300,90 | Col `d_empresa.nome` (mode Single) |
| `v_bar_proventos_ano` | `columnChart` | 360,60,560,300 | Category: Col `f_proventos_anual.ano`; Values: Col `f_proventos_anual.total_proventos` (agregado por soma) |
| `v_card_preco` | `card` | 940,60,300,90 | Measure `_Medidas.Preço Atual Ação` |
| `v_card_teto` | `card` | 940,160,300,90 | Measure `_Medidas.Preço-Teto` |
| `v_card_margem` | `card` | 940,260,300,90 | Measure `_Medidas.Margem vs Teto %` |
| `v_card_pos52` | `card` | 40,380,220,110 | Measure `_Medidas.Posição 52 Semanas` |
| `v_card_anos_consec` | `card` | 280,380,220,110 | Measure `_Medidas.Anos Consecutivos` |
| `v_card_cagr` | `card` | 520,380,220,110 | Measure `_Medidas.Crescimento Dividendo CAGR 5a` |
| `v_card_pl` | `card` | 760,380,220,110 | Measure `_Medidas.P/L` |

Para o eixo de datas do gráfico de proventos, usar a coluna `f_proventos_anual.ano` como `Category` — no PBIR o `columnChart` usa `queryState.Category.projections` para o eixo e `queryState.Values.projections` para o valor. Exemplo do `v_bar_proventos_ano/visual.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "v_bar_proventos_ano",
  "position": { "x": 360, "y": 60, "z": 100, "height": 300, "width": 560, "tabOrder": 100 },
  "visual": {
    "visualType": "columnChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "f_proventos_anual" } }, "Property": "ano" } }, "queryRef": "f_proventos_anual.ano", "nativeQueryRef": "ano" }
          ]
        },
        "Values": {
          "projections": [
            { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "f_proventos_anual" } }, "Property": "total_proventos" } }, "queryRef": "f_proventos_anual.total_proventos", "nativeQueryRef": "total_proventos" }
          ]
        }
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

O `v_slicer_ticker/visual.json` segue o padrão do `v_slicer_setor` (Tarefa 12) usando `d_empresa.nome`, com `objects.data` em modo `Single`.

- [ ] **Step 2: Página 05 — Ranking Barsi**

Create `pagina05ranking/page.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "pagina05ranking",
  "displayName": "Ranking Barsi",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

Visuais:

| name | visualType | position (x,y,w,h) | projections |
|---|---|---|---|
| `v_slicer_besst_rk` | `slicer` | 40,60,300,200 | Col `d_empresa.besst` |
| `v_slicer_yield_rk` | `slicer` | 40,280,300,90 | Col `p_YieldDesejado.Valor` (mode Single) |
| `v_bar_ranking` | `barChart` | 360,60,880,600 | Category: Col `d_empresa.nome`; Values: Measure `_Medidas.Score Barsi`; sort por `Score Barsi` Descending |

O `v_bar_ranking/visual.json` usa `visualType: "barChart"`, `queryState.Category.projections` = `d_empresa.nome`, `queryState.Values.projections` = `_Medidas.Score Barsi`, e um `sortDefinition` por `Score Barsi` `Descending` (mesma estrutura do sort da Tarefa 12).

- [ ] **Step 3: Página 06 — Simulador de Renda Passiva**

Create `pagina06simulador/page.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "pagina06simulador",
  "displayName": "Simulador de Renda Passiva",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

Visuais:

| name | visualType | position (x,y,w,h) | projections |
|---|---|---|---|
| `v_sl_aporte` | `slicer` | 40,60,280,90 | Col `p_Sim_AporteMensal.Valor` (Single) |
| `v_sl_dy` | `slicer` | 40,160,280,90 | Col `p_Sim_DYEsperado.Valor` (Single) |
| `v_sl_cresc` | `slicer` | 40,260,280,90 | Col `p_Sim_CrescAporte.Valor` (Single) |
| `v_sl_anos` | `slicer` | 40,360,280,90 | Col `p_Sim_Anos.Valor` (Single) |
| `v_card_patrimonio` | `card` | 340,60,300,120 | Measure `_Medidas.Patrimônio Projetado` |
| `v_card_renda` | `card` | 660,60,300,120 | Measure `_Medidas.Renda Passiva Mensal Projetada` |
| `v_card_aportado` | `card` | 980,60,260,120 | Measure `_Medidas.Total Aportado` |
| `v_area_evolucao` | `areaChart` | 340,200,900,460 | Category: Col `d_horizonte.ano`; Values: Measures `_Medidas.Patrimônio até o Ano` e `_Medidas.Renda Mensal até o Ano` |

O `v_area_evolucao/visual.json` usa `visualType: "areaChart"` com `queryState.Category.projections` = `d_horizonte.ano` e `queryState.Values.projections` com as DUAS medidas (dois objetos no array).

- [ ] **Step 4: Registrar as páginas em `pages.json`**

Substituir o conteúdo de `pages.json` por:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
  "pageOrder": [
    "pagina01panorama",
    "pagina02explorar",
    "pagina03dividendos",
    "pagina04detalhe",
    "pagina05ranking",
    "pagina06simulador"
  ],
  "activePageName": "pagina03dividendos"
}
```

- [ ] **Step 5: Validar todos os JSON do relatório**

Run: `python -c "import json,glob; n=[json.load(open(f,encoding='utf-8')) for f in glob.glob('Panorama Macro BCB.Report/definition/pages/**/*.json', recursive=True)]; print(len(n),'arquivos json ok')"`
Expected: imprime a contagem e `... json ok` sem exceção.

- [ ] **Step 6: Commit**

```bash
git add "Panorama Macro BCB.Report/definition/pages"
git commit -m "feat(report): paginas Detalhe da Acao, Ranking Barsi e Simulador

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 14: Página 01 — contexto do yield-alvo

**Files:**
- Modify: `.../pages/pagina01panorama/visuals/v_titulo/visual.json` (texto)
- Create: `.../pagina01panorama/visuals/v_card_yield_ref/visual.json`

- [ ] **Step 1: Card de referência do yield-alvo**

Create `v_card_yield_ref/visual.json` mostrando a Selic como piso do yield-alvo (reusa a medida `Selic Meta`):

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
  "name": "v_card_yield_ref",
  "position": { "x": 40, "y": 600, "z": 500, "height": 100, "width": 300, "tabOrder": 500 },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Selic Meta" } }, "queryRef": "_Medidas.Selic Meta", "nativeQueryRef": "Selic Meta" }
          ]
        }
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

- [ ] **Step 2: Validar JSON e commit**

Run: `python -c "import json; json.load(open('Panorama Macro BCB.Report/definition/pages/pagina01panorama/visuals/v_card_yield_ref/visual.json',encoding='utf-8')); print('ok')"`
Expected: `ok`

```bash
git add "Panorama Macro BCB.Report/definition/pages/pagina01panorama"
git commit -m "feat(report): card Selic como piso do yield-alvo na pagina Cenario Macro

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Fase 4 — DQ, documentação e verificação

### Task 15: Contratos de dados e dq_check

**Files:**
- Modify/Create: `contracts/panorama/d_empresa.yml`, `contracts/panorama/f_proventos.yml`
- Modify: `scripts/dq_check_panorama.py`

- [ ] **Step 1: Ler os contratos e o dq_check atuais**

Run: `python -c "import glob; print('\n'.join(glob.glob('contracts/panorama/*')))"` e abrir `scripts/dq_check_panorama.py` para conhecer o formato vigente antes de editar.

- [ ] **Step 2: Adicionar regras ao contrato de `d_empresa`**

Acrescentar ao contrato de `d_empresa` a coluna `besst` com domínio permitido `["B","E","SA","SE","T","—"]` e `not_null`. Seguir exatamente o schema YAML já usado nos outros contratos da pasta (mesma indentação/nomes de chave).

- [ ] **Step 3: Adicionar regra de janela ao contrato de `f_proventos`**

Acrescentar verificação de que `data_pagamento` cobre ~10 anos (min(data_pagamento) ≤ hoje − 9 anos), no mesmo formato do contrato existente.

- [ ] **Step 4: Estender `dq_check_panorama.py`**

Adicionar uma verificação que importa o oráculo e valida o mapeamento BESST contra a lista de tickers carregada, e uma verificação de que o preço-teto é positivo quando há dividendo médio > 0. Reusar `from scripts.barsi_calc import besst_de_ticker, preco_teto, dividendo_medio_anual`. Seguir o padrão de saída (relatório em `outputs/dq/...`) já existente no script.

- [ ] **Step 5: Rodar o dq_check e os testes**

Run: `python -m pytest tests/test_barsi_calc.py -q` → Expected: PASS.
Run: `python scripts/dq_check_panorama.py` (com `BRAPI_TOKEN` no ambiente) → Expected: relatório gerado sem erro fatal; falhas de cobertura apenas sinalizadas.

- [ ] **Step 6: Commit**

```bash
git add contracts/panorama scripts/dq_check_panorama.py
git commit -m "feat(dq): contratos e checagens para besst, teto e janela de 10a

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 16: Registro de decisão e documentação

**Files:**
- Create: `outputs/decisions/2026-08-06-camada-barsi.md`
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1: Registrar decisões**

Create `outputs/decisions/2026-08-06-camada-barsi.md` documentando: (a) ambiguidade de setor da brapi → override por ticker em `d_besst`; (b) teto sobre média de 5 anos (Bazin) vs consistência em 10 anos; (c) conflito de identidade resolvido (tema padrão por decisão do dono, apesar da diretriz organizacional de marca); (d) `IbovTickers` mantém o nome do parâmetro apesar de virar "universo BESST ampliado" (evita quebrar partições); (e) simulador usa "crescimento do aporte" (g) em vez de "crescimento do dividendo" para uma fórmula fechada e sem dupla contagem.

- [ ] **Step 2: Atualizar `README.md`**

Acrescentar seção "Método Barsi" descrevendo as páginas (Screener, Detalhe, Ranking, Simulador), as medidas de teto/consistência/score e o universo BESST ampliado. Manter o tom de portfólio público.

- [ ] **Step 3: Atualizar `CLAUDE.md` do projeto (cirúrgico)**

Acrescentar às tabelas do modelo: `d_besst`, `f_proventos_anual`, tabelas `p_*`, `d_horizonte`; às páginas: 04/05/06; aos gotchas: override BESST por ticker, teto=5a×consistência=10a, `range=10y` no Yahoo. Atualizar a lista de páginas e o parágrafo "Sem identidade de marca" para referenciar a decisão registrada.

- [ ] **Step 4: Commit**

```bash
git add outputs/decisions README.md CLAUDE.md
git commit -m "docs: registro de decisao Barsi + README e CLAUDE atualizados

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 17: Verificação manual no Power BI Desktop (gate final)

**Files:** nenhum (verificação interativa)

> DAX e visuais só podem ser validados de fato no Desktop. Este passo NÃO é automatizável.

- [ ] **Step 1: Abrir e atualizar**

Abrir `Panorama Financeiro.pbip` no Desktop, definir privacidade das fontes como Público, repreencher `BrapiToken`, e clicar em Atualizar.

- [ ] **Step 2: Verificar o modelo**
  - As tabelas novas aparecem (`d_besst`, `f_proventos_anual`, `p_*`, `d_horizonte`).
  - `d_empresa[besst]` está preenchida e correta (checar 1 banco, 1 seguradora, 1 saneamento, 1 energia, 1 telecom).
  - Marcar `d_calendario` como Tabela de Data (se o Desktop resetar).

- [ ] **Step 3: Verificar as páginas**
  - Screener: mudar o slicer de Yield Desejado e confirmar que `Preço-Teto`/`Sinal`/`Ações Abaixo do Teto` recalculam.
  - Detalhe: selecionar um ticker e ver 10 anos de proventos + consistência.
  - Ranking: ordenação por Score coerente.
  - Simulador: mover os 4 sliders e ver patrimônio/renda/curva reagirem; conferir 1 cenário contra o oráculo: `python -c "from scripts.barsi_calc import patrimonio_projetado, renda_passiva_mensal as r; fv=patrimonio_projetado(1000,0.06,0.05,20); print(round(fv,2), round(r(fv,0.06),2))"` e comparar com os cards.

- [ ] **Step 4: Revisar `git diff` e commitar apenas mudanças intencionais**

O Desktop pode reformatar arquivos e reescrever `BrapiToken`. Conferir `git status`/`git diff`; **não** commitar o token (expressions.tmdl segue protegido por skip-worktree). Commitar só ajustes legítimos de layout, se houver:

```bash
git add -p
git commit -m "chore(report): ajustes de layout pos-verificacao no Desktop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 5: Finalizar a branch**

Usar a skill `superpowers:finishing-a-development-branch` para decidir merge/PR.

---

## Notas de execução

- **Ordem obrigatória:** Fase 0 → 1 → 2 → 3 → 4. Medidas (Fase 2) dependem das tabelas (Fase 1); relatório (Fase 3) depende das medidas.
- **Reabrir o Desktop só ao final** (Task 17) para evitar reformatações intermediárias que poluem os diffs. As Fases 1–3 são edições de arquivo puras (TMDL/JSON), commitáveis sem abrir o Desktop.
- **`lineageTag`s** usados no plano são placeholders únicos; se o Desktop reclamar de colisão, deixá-lo regenerar ao salvar.
