"""Gera um snapshot Barsi a partir das mesmas APIs públicas do modelo Power BI.

Reutiliza o oráculo ``scripts/barsi_calc.py`` (fonte de verdade das fórmulas,
espelhada em DAX) para produzir, sem abrir o Power BI:

* Snapshot macro (BCB SGS) — Selic, CDI, IPCA 12m, IGP-M, Dólar PTAX.
* Ranking de consistência de dividendos (Yahoo Finance, sem token) — anos
  pagando, anos consecutivos, cortes, CAGR 5a e dividendo médio anual (Bazin).
* Colunas dependentes de preço (preço-teto, margem, DY, Score Barsi) quando a
  variável de ambiente ``BRAPI_TOKEN`` está definida; caso contrário, omitidas.

Saídas (Markdown + CSV) em ``outputs/insights/``.

Uso:
    BRAPI_TOKEN=xxxx python scripts/barsi_ranking.py      # ranking completo
    python scripts/barsi_ranking.py                       # sem preço (só consistência)
    python scripts/barsi_ranking.py --universo todos      # amplia p/ todos os IbovTickers
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.barsi_calc import (  # noqa: E402
    BESST_NOME,
    BESST_OVERRIDE,
    anos_consecutivos,
    anos_pagando,
    cagr_dividendo,
    cortes_dividendo,
    dividendo_medio_anual,
    is_besst,
    preco_teto,
    score_barsi,
)

ROOT = Path(__file__).resolve().parents[1]
EXPRESSIONS = ROOT / "Panorama Macro BCB.SemanticModel" / "definition" / "expressions.tmdl"
OUT_DIR = ROOT / "outputs" / "insights"

ANO_REF = date.today().year
YIELD_DESEJADO = 0.06  # piso Bazin padrão (6% a.a.), igual ao default do modelo

MACRO_SERIES = {
    "432": "Selic Meta (% a.a.)",
    "12": "CDI (% a.d.)",
    "13522": "IPCA 12m (%)",
    "189": "IGP-M mês (%)",
    "1": "Dólar PTAX (R$)",
}


def _get_json(url: str, timeout: int = 30):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 (APIs públicas)
        return json.loads(resp.read().decode("utf-8"))


def read_tickers(universo: str) -> list[str]:
    """Lê IbovTickers do TMDL (DRY com o modelo). 'besst' filtra o universo BESST."""
    text = EXPRESSIONS.read_text(encoding="utf-8")
    m = re.search(r'expression IbovTickers = "([^"]+)"', text)
    todos = [t.strip() for t in (m.group(1).split(",") if m else []) if t.strip()]
    if universo == "besst":
        return [t for t in todos if t in BESST_OVERRIDE]
    return todos


def fetch_macro() -> list[tuple[str, str, str]]:
    linhas = []
    for codigo, label in MACRO_SERIES.items():
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"
        try:
            d = _get_json(url)[0]
            linhas.append((label, d["valor"], d["data"]))
        except Exception as e:  # noqa: BLE001
            linhas.append((label, "n/d", str(e)[:30]))
    return linhas


def fetch_dividendos_por_ano(ticker: str) -> dict[int, float]:
    """Proventos anuais (Yahoo, 10 anos). Chave = ano, valor = soma no ano."""
    q = urlencode({"range": "10y", "interval": "1d", "events": "div"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA?{q}"
    try:
        j = _get_json(url)
        divs = j["chart"]["result"][0]["events"]["dividends"]
    except Exception:  # noqa: BLE001
        return {}
    por_ano: dict[int, float] = {}
    for ev in divs.values():
        ano = datetime.fromtimestamp(ev["date"], tz=timezone.utc).year
        por_ano[ano] = por_ano.get(ano, 0.0) + float(ev["amount"])
    return por_ano


def fetch_quote(ticker: str, token: str) -> dict:
    q = urlencode({"token": token})
    url = f"https://brapi.dev/api/quote/{ticker}?{q}"
    try:
        r = _get_json(url)["results"][0]
        return {
            "preco": r.get("regularMarketPrice"),
            "pl": r.get("priceEarnings"),
            "nome": r.get("longName") or r.get("shortName"),
        }
    except Exception:  # noqa: BLE001
        return {}


def build_rows(tickers: list[str], token: str | None) -> list[dict]:
    rows = []
    for i, tk in enumerate(tickers, 1):
        por_ano = fetch_dividendos_por_ano(tk)
        div_medio = dividendo_medio_anual(por_ano, ANO_REF, janela=5)
        row = {
            "ticker": tk,
            "besst": BESST_NOME.get(BESST_OVERRIDE.get(tk, "—"), "Fora BESST"),
            "div_medio_5a": round(div_medio, 4),
            "anos_pagando_10a": anos_pagando(por_ano, ANO_REF, 10),
            "anos_consecutivos": anos_consecutivos(por_ano, ANO_REF, 10),
            "cortes_10a": cortes_dividendo(por_ano, ANO_REF, 10),
            "cagr_5a": round(cagr_dividendo(por_ano, ANO_REF, 5), 4),
            "preco": None,
            "pl": None,
            "preco_teto": round(preco_teto(div_medio, YIELD_DESEJADO), 2),
            "margem_teto": None,
            "dy_medio_5a": None,
            "score": None,
        }
        if token:
            q = fetch_quote(tk, token)
            preco, pl = q.get("preco"), q.get("pl")
            row["preco"] = preco
            row["pl"] = pl
            if preco and preco > 0:
                margem = (row["preco_teto"] - preco) / preco
                dy_medio = div_medio / preco
                row["margem_teto"] = round(margem, 4)
                row["dy_medio_5a"] = round(dy_medio, 4)
                row["score"] = score_barsi(
                    dy_medio=dy_medio,
                    anos_consec=row["anos_consecutivos"],
                    is_besst=is_besst(BESST_OVERRIDE.get(tk, "—")),
                    margem=margem,
                    pl=pl if pl else 0.0,
                )
            time.sleep(0.1)  # cortesia com a brapi
        rows.append(row)
        print(f"  [{i}/{len(tickers)}] {tk}", file=sys.stderr)
    # ordena por score (se houver) senão por consistência + dividendo médio
    if token:
        rows.sort(key=lambda r: (r["score"] if r["score"] is not None else -1), reverse=True)
    else:
        rows.sort(key=lambda r: (r["anos_consecutivos"], r["div_medio_5a"]), reverse=True)
    return rows


def write_outputs(macro, rows, com_preco: bool) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()
    csv_path = OUT_DIR / f"barsi_ranking_{hoje}.csv"
    md_path = OUT_DIR / f"barsi_ranking_{hoje}.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = [
        f"# Snapshot Barsi — {hoje}",
        "",
        "> Gerado por `scripts/barsi_ranking.py` a partir de BCB SGS e Yahoo Finance"
        + (" + brapi.dev" if com_preco else " (sem preço — defina `BRAPI_TOKEN` para o ranking completo)")
        + ". Fórmulas: `scripts/barsi_calc.py` (mesma lógica das medidas DAX).",
        "",
        "## Cenário macro (BCB)",
        "",
        "| Indicador | Valor | Data |",
        "|---|---:|---|",
    ]
    lines += [f"| {lbl} | {val} | {dt} |" for lbl, val, dt in macro]
    lines += [
        "",
        f"## Ranking — universo {'BESST' if len(rows) < 60 else 'ampliado'} ({len(rows)} tickers)",
        "",
    ]
    if com_preco:
        lines += [
            "| # | Ticker | Setor | Score | Preço | Teto (6%) | Margem | DY 5a | Anos consec. | Cortes 10a | CAGR 5a |",
            "|--:|---|---|--:|--:|--:|--:|--:|--:|--:|--:|",
        ]
        for i, r in enumerate(rows, 1):
            lines.append(
                f"| {i} | {r['ticker']} | {r['besst']} | "
                f"{_f(r['score'],1)} | {_f(r['preco'],2)} | {_f(r['preco_teto'],2)} | "
                f"{_pct(r['margem_teto'])} | {_pct(r['dy_medio_5a'])} | "
                f"{r['anos_consecutivos']} | {r['cortes_10a']} | {_pct(r['cagr_5a'])} |"
            )
    else:
        lines += [
            "| # | Ticker | Setor | Div. médio 5a | Teto (6%) | Anos consec. | Anos pagando | Cortes 10a | CAGR 5a |",
            "|--:|---|---|--:|--:|--:|--:|--:|--:|",
        ]
        for i, r in enumerate(rows, 1):
            lines.append(
                f"| {i} | {r['ticker']} | {r['besst']} | {_f(r['div_medio_5a'],2)} | "
                f"{_f(r['preco_teto'],2)} | {r['anos_consecutivos']} | {r['anos_pagando_10a']} | "
                f"{r['cortes_10a']} | {_pct(r['cagr_5a'])} |"
            )
    lines += [
        "",
        "---",
        "_Metodologia e ressalvas em `INSIGHTS.md`. Não é recomendação de investimento._",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, csv_path


def _f(v, n):
    return f"{v:.{n}f}" if isinstance(v, (int, float)) else "—"


def _pct(v):
    return f"{v*100:.1f}%" if isinstance(v, (int, float)) else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description="Snapshot Barsi via APIs públicas.")
    ap.add_argument("--universo", choices=["besst", "todos"], default="besst")
    args = ap.parse_args()

    token = os.environ.get("BRAPI_TOKEN") or None
    tickers = read_tickers(args.universo)
    print(f"Macro (BCB)…", file=sys.stderr)
    macro = fetch_macro()
    print(f"Dividendos/preço de {len(tickers)} tickers "
          f"({'com' if token else 'sem'} brapi)…", file=sys.stderr)
    rows = build_rows(tickers, token)
    md_path, csv_path = write_outputs(macro, rows, com_preco=bool(token))
    print(f"OK -> {md_path}")
    print(f"OK -> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
