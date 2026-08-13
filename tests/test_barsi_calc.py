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
