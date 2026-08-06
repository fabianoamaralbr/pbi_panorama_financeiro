"""Data quality check for the Panorama Financeiro semantic model.

Validates live source data against the contracts in ``contracts/panorama/`` by
hitting the same public APIs the Power BI model consumes:

* BCB SGS (macro)       -- no auth
* Yahoo Finance (divs)  -- no auth
* brapi.dev (quotes)    -- token read from the ``BRAPI_TOKEN`` env var (never hardcoded)

Run:
    BRAPI_TOKEN=xxxx python scripts/dq_check_panorama.py     # full run
    python scripts/dq_check_panorama.py                      # skips brapi checks (WARN)

Emits a DQ report to ``outputs/dq/panorama/`` and process metrics to
``outputs/metrics/dq_check_panorama/`` following the squad observability format.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.barsi_calc import besst_de_ticker, dividendo_medio_anual, preco_teto

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
EXPRESSIONS = ROOT / "Panorama Macro BCB.SemanticModel" / "definition" / "expressions.tmdl"

# codigo -> (label, tipo, freq)
MACRO_SERIES: dict[str, tuple[str, str, str]] = {
    "432": ("Selic Meta", "taxa", "diaria"),
    "12": ("CDI", "taxa", "diaria"),
    "433": ("IPCA mensal", "taxa", "mensal"),
    "13522": ("IPCA 12m", "taxa", "mensal"),
    "189": ("IGP-M mensal", "taxa", "mensal"),
    "1": ("Dolar PTAX", "preco", "diaria"),
    "4380": ("PIB mensal", "indice", "mensal"),
}
SAMPLE_TICKERS_DIV = ["PETR4", "VALE3", "ITUB4", "BBAS3", "WEGE3"]


def _get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 30):
    req = Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 (public APIs only)
        return json.loads(resp.read().decode("utf-8"))


def read_ibov_tickers() -> list[str]:
    """Parse the IbovTickers parameter from the TMDL so we stay DRY with the model."""
    text = EXPRESSIONS.read_text(encoding="utf-8")
    m = re.search(r'expression IbovTickers = "([^"]+)"', text)
    if not m:
        logger.warning("IbovTickers não encontrado no TMDL; usando amostra.")
        return SAMPLE_TICKERS_DIV
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


class Result:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, check_id: str, status: str, detail: str) -> None:
        self.checks.append({"check": check_id, "status": status, "detail": detail})
        logger.info("[%s] %s — %s", status.upper(), check_id, detail)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c["status"] == "error")

    @property
    def warned(self) -> int:
        return sum(1 for c in self.checks if c["status"] == "warn")


def check_macro(res: Result) -> None:
    presentes = 0
    today = date.today()
    for codigo, (label, tipo, freq) in MACRO_SERIES.items():
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"
        try:
            data = _get_json(url)
        except Exception as exc:  # noqa: BLE001
            res.add(f"macro.{codigo}.fetch", "error", f"{label}: falha ao buscar ({exc})")
            continue
        if not data:
            res.add(f"macro.{codigo}.presente", "error", f"{label}: série vazia")
            continue
        presentes += 1
        obs = data[-1]
        valor = float(str(obs["valor"]).replace(",", "."))
        dt = datetime.strptime(obs["data"], "%d/%m/%Y").date()
        limite = 15 if freq == "diaria" else 70
        status = "ok" if (today - dt).days <= limite else "warn"
        res.add(f"macro.{codigo}.frescor", status, f"{label}: última obs {dt} = {valor}")
        if tipo == "taxa" and not (-50 <= valor <= 100):
            res.add(f"macro.{codigo}.dominio", "error", f"{label}: {valor} fora de [-50,100]")
        if codigo == "1" and not (1 <= valor <= 20):
            res.add("macro.1.dominio", "error", f"PTAX {valor} fora de [1,20]")
    res.add(
        "macro.series_presentes",
        "ok" if presentes == len(MACRO_SERIES) else "error",
        f"{presentes}/{len(MACRO_SERIES)} séries presentes",
    )


def check_acoes(res: Result, tickers: list[str]) -> None:
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    if not token:
        res.add("acoes.brapi", "warn", "BRAPI_TOKEN ausente — checks de d_empresa pulados")
    else:
        com_preco = 0
        total = 0
        # brapi free aceita apenas 1 ticker por chamada (igual ao modelo, fnBrapiQuote).
        for ticker in tickers:
            url = f"https://brapi.dev/api/quote/{ticker}?" + urlencode({"token": token})
            try:
                data = _get_json(url)
            except Exception as exc:  # noqa: BLE001
                res.add("acoes.fetch", "warn", f"{ticker} falhou ({exc})")
                continue
            for r in data.get("results", []):
                total += 1
                preco = r.get("regularMarketPrice")
                lo, hi = r.get("fiftyTwoWeekLow"), r.get("fiftyTwoWeekHigh")
                if preco is not None:
                    com_preco += 1
                    if preco <= 0:
                        res.add("acoes.preco_positivo", "error", f"{r.get('symbol')}: preço {preco}")
                if lo is not None and hi is not None and lo > hi:
                    res.add("acoes.faixa_52s", "error", f"{r.get('symbol')}: min>max")
        cobertura = com_preco / total if total else 0.0
        res.add(
            "acoes.cobertura_preco",
            "ok" if cobertura >= 0.80 else "warn",
            f"cobertura de preço {cobertura:.1%} ({com_preco}/{total})",
        )

    # Proventos + DY plausível (amostra; Yahoo é sem auth)
    limite = date.today() - timedelta(days=400)
    for ticker in SAMPLE_TICKERS_DIV:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA?"
            + urlencode({"range": "1y", "interval": "1d", "events": "div"})
        )
        try:
            data = _get_json(url)
            result = (data.get("chart", {}).get("result") or [{}])[0]
            divs = (result.get("events", {}) or {}).get("dividends", {}) or {}
        except Exception as exc:  # noqa: BLE001
            res.add(f"proventos.{ticker}.fetch", "warn", f"falha Yahoo ({exc})")
            continue
        soma = 0.0
        for d in divs.values():
            valor = float(d.get("amount", 0))
            dt = datetime.fromtimestamp(int(d["date"]), tz=timezone.utc).date()
            if valor <= 0:
                res.add(f"proventos.{ticker}.valor", "error", f"provento {valor} <= 0")
            if dt < limite:
                res.add(f"proventos.{ticker}.janela", "warn", f"provento antigo {dt}")
            soma += max(valor, 0)
        preco = result.get("meta", {}).get("regularMarketPrice")
        if preco and preco > 0:
            dy = soma / preco
            status = "ok" if 0 <= dy <= 0.30 else "error"
            res.add(f"proventos.{ticker}.dy", status, f"DY 12m = {dy:.2%}")


def check_barsi_besst(res: Result, tickers: list[str]) -> None:
    """Validate that every ticker in the universe resolves to a BESST sigla via the oracle.

    Tickers that resolve to '—' are expected (non-BESST) and not errors; the check simply
    confirms the oracle returns a non-empty, valid value for all tickers so the mapping
    table is consistent with the loaded universe.
    """
    valid_siglae = {"B", "E", "SA", "SE", "T", "—"}
    unresolvable: list[str] = []
    for ticker in tickers:
        sigla = besst_de_ticker(ticker, None)  # setor not available here — override dict covers known ones
        if sigla not in valid_siglae:
            unresolvable.append(ticker)
    if unresolvable:
        res.add(
            "barsi.besst_resolution",
            "error",
            f"{len(unresolvable)} tickers retornam sigla inválida: {unresolvable[:10]}",
        )
    else:
        res.add(
            "barsi.besst_resolution",
            "ok",
            f"todos os {len(tickers)} tickers resolvem para sigla BESST válida",
        )


def check_barsi_teto(res: Result) -> None:
    """Validate oracle invariant: preco_teto > 0 when dividendo_medio_anual > 0.

    Uses synthetic data so no live API is required — pure formula consistency check.
    """
    ano_ref = date.today().year
    casos_falhos: list[str] = []
    # Representative test cases: at least one year with dividends, yield_desejado = 0.06
    test_cases = [
        ("BBAS3", {ano_ref - 1: 2.50, ano_ref - 2: 2.00}),
        ("EGIE3", {ano_ref - 1: 3.10}),
        ("SBSP3", {ano_ref - 1: 1.20, ano_ref - 3: 0.80}),
    ]
    for ticker, por_ano in test_cases:
        div_medio = dividendo_medio_anual(por_ano, ano_ref=ano_ref)
        teto = preco_teto(div_medio=div_medio, yield_desejado=0.06)
        if div_medio > 0 and teto <= 0:
            casos_falhos.append(ticker)
    if casos_falhos:
        res.add(
            "barsi.teto_positivo",
            "error",
            f"preco_teto <= 0 apesar de div_medio > 0 para: {casos_falhos}",
        )
    else:
        res.add(
            "barsi.teto_positivo",
            "ok",
            "preco_teto > 0 sempre que dividendo_medio_anual > 0 (invariante verificado)",
        )


def main() -> int:
    t0 = time.perf_counter()
    res = Result()
    tickers = read_ibov_tickers()
    logger.info("Validando %d tickers + %d séries macro", len(tickers), len(MACRO_SERIES))

    check_macro(res)
    check_acoes(res, tickers)
    check_barsi_besst(res, tickers)
    check_barsi_teto(res)

    status = "error" if res.failed else ("warn" if res.warned else "success")
    elapsed = round(time.perf_counter() - t0, 2)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    report = {
        "pipeline": "dq_check_panorama",
        "agent": "quality",
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "checks_total": len(res.checks),
        "checks_error": res.failed,
        "checks_warn": res.warned,
        "checks": res.checks,
    }
    dq_dir = ROOT / "outputs" / "dq" / "panorama"
    metrics_dir = ROOT / "outputs" / "metrics" / "dq_check_panorama"
    dq_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    (dq_dir / f"{ts}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (metrics_dir / f"{ts}.json").write_text(
        json.dumps(
            {k: report[k] for k in ("pipeline", "agent", "status", "elapsed_seconds", "checks_total", "checks_error", "checks_warn")},
            indent=2,
        )
    )

    logger.info("=" * 60)
    logger.info("DQ %s — %d checks (%d erro, %d warn) em %.2fs", status.upper(), len(res.checks), res.failed, res.warned, elapsed)
    return 1 if status == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
