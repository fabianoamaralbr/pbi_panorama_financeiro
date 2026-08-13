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
    s_pl = max(0.0, min((20 - pl) / 15, 1.0)) * 10 if 0 < pl <= 20 else 0.0
    total = s_dy + s_consec + s_besst + s_margem + s_pl
    return round(max(0.0, min(total, 100.0)), 2)


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
