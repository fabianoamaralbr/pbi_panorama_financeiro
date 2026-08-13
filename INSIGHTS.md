# Achados — Panorama Financeiro

> **Snapshot de 13/08/2026.** Números gerados a partir de dados públicos ao vivo por
> `scripts/barsi_ranking.py` (BCB SGS + Yahoo Finance + brapi.dev), usando as mesmas
> fórmulas das medidas DAX (`scripts/barsi_calc.py`). Tabela completa em
> [`outputs/insights/barsi_ranking_2026-08-13.md`](outputs/insights/barsi_ranking_2026-08-13.md).
> **Não é recomendação de investimento** — ver ressalvas no fim.

## Pergunta de negócio

> Num cenário de juros altos, **quais pagadoras de dividendos dos setores perenes (BESST)
> estão sendo negociadas abaixo do seu preço-teto** (o preço que entrega o yield mínimo
> desejado), e **quão consistente** é esse histórico de proventos?

O painel conecta dois domínios que normalmente vivem separados — **macro** (o custo de
oportunidade) e **renda variável** (a oportunidade em si) — para responder isso.

## 1. O macro define a régua (e a régua está alta)

| Indicador | Valor | Leitura |
|---|---:|---|
| Selic Meta | **14,00% a.a.** | Política monetária restritiva. |
| IPCA 12m | **4,44%** | Acima do centro da meta (3%), dentro da banda superior. |
| Juro real *ex-post* | **≈ 9,1%** | `(1,14 / 1,0444) − 1`. Muito alto historicamente. |
| Dólar PTAX | R$ 5,19 | — |
| IGP-M (mês) | −1,16% | Deflação no atacado no mês. |

**Insight central:** com a Selic a **14%**, o *yield-alvo* padrão de **6%** usado no
preço-teto (Bazin) é **conservador demais como piso** — o CDI paga mais que o dobro sem
risco de renda variável. É exatamente por isso que a página *Cenário Macro* traz a **Selic
como piso do yield-alvo**: um investidor racional exige *prêmio* sobre o CDI, então o teto
"justo" de uma ação deveria usar um yield desejado maior — o que **derruba** os preços-teto
e **encolhe** a lista de "Comprar". O slicer *Yield Desejado* (what-if) permite estressar
isso ao vivo. Este é o principal "e daí?" do projeto: **a atratividade da carteira de
dividendos é função do juro básico.**

## 2. O screener Barsi (universo BESST, 38 tickers)

Ordenado por **Score Barsi** (0–100; pesos: DY médio 5a 30 · anos consecutivos 25 ·
BESST 15 · margem vs teto 20 · P/L 10).

**Top do ranking (a 6% de yield-alvo):**

| # | Ticker | Setor | Score | Margem vs Teto | DY 5a | Anos consec. | Cortes 10a |
|--:|---|---|--:|--:|--:|--:|--:|
| 1 | CMIG4 | Energia | 99,3 | +104% | 12,2% | 10 | 3 |
| 2 | BBAS3 | Bancos | 91,0 | +55% | 9,3% | 10 | 3 |
| 3 | TAEE11 | Energia | 85,1 | +67% | 10,0% | 10 | 3 |
| 4 | BMGB4 | Bancos | 82,3 | +32% | 7,9% | 7 | 2 |
| 5 | ABCB4 | Bancos | 80,6 | +23% | 7,3% | 9 | 3 |

**Leituras:**

- **Bancos dominam o topo** (BBAS3, BMGB4, ABCB4, BBDC3, BBDC4): DY alto + histórico longo.
- **~14 das 34 ações com preço** (~41%) estão **abaixo do teto** a 6% ("Comprar"). A 6% de
  yield-alvo a lista é generosa; subindo o alvo para perto do CDI, ela encolhe drasticamente
  (ver Insight 1).
- **Score alto ≠ ausência de risco.** CMIG4 lidera com margem de 104%, mas tem **3 cortes**
  de dividendo em 10 anos e CAGR de 56,7% (base volátil) — o Score premia o desconto atual,
  mas a aba *Detalhe da Ação* revela a irregularidade. **Pares mais "regulares"**: EGIE3 e
  BBDC3 (10 anos consecutivos), embora com menos desconto.
- **Acima do teto (caras por Bazin):** ITUB4 (−18%), PSSA3 (−44%), EQTL3 (−57%),
  SBSP3 (−72%), BPAC11 (−73%). São bons negócios com **crescimento já no preço** — o método
  Barsi (focado em renda, não em ganho de capital) naturalmente as classifica como "Aguardar".

## 3. Consistência importa mais que yield pontual

O método pondera **anos consecutivos pagando** (25 pts) e penaliza **cortes**. Isso separa
o pagador estrutural do eventual: WIZC3 tem 10 anos consecutivos mas **6 cortes** (yield alto,
porém decrescente, CAGR −3,3%), enquanto EGIE3 combina 10 anos consecutivos com crescimento —
perfis muito diferentes que um ranking só por "DY 12m" trataria como iguais.

## Ressalvas e limitações (leia antes de usar)

1. **O Score é uma heurística, não um modelo validado.** Os pesos (30/25/15/20/10) são
   uma opinião estruturada sobre o método Barsi, **não** foram *backtestados* contra retorno
   futuro. Próximo passo natural: testar se score mais alto prevê DY/retorno realizado no ano
   seguinte. Trate o ranking como **ponto de partida de pesquisa**, não como recomendação.
2. **Qualidade de dados:** neste snapshot, 4 de 38 tickers (CPLE6, ELET6, NEOE3, AESB3)
   voltaram **sem preço** da brapi → cobertura de preço ~89,5%. Sem preço, não há teto/score.
   As medidas da pasta *Diagnóstico* sinalizam isso no relatório.
3. **Sobrevivência e listagem recente:** algumas do universo têm poucos anos de histórico
   (ex.: ELET3/6 pós-privatização zeraram a sequência de dividendos) e aparecem no fim do
   ranking corretamente — mas não há tratamento de *survivorship bias* no universo escolhido.
4. **Sensibilidade ao yield-alvo:** todo o preço-teto escala com `1 / yield_desejado`. A 6%
   a lista de "Comprar" é ampla; a 10% ela encolhe. **A conclusão depende da premissa** —
   por isso é um parâmetro *what-if*, não uma constante.
5. **Dividendos via Yahoo** não distinguem dividendo de JCP nem ajustam impostos; são
   proventos brutos por data de pagamento.

## Como reproduzir

```bash
# Ranking completo (com preço/score) — requer token free do brapi
BRAPI_TOKEN=seu_token python scripts/barsi_ranking.py --universo besst

# Sem token: só consistência de dividendos (Yahoo/BCB, público)
python scripts/barsi_ranking.py
```

Saídas datadas em `outputs/insights/`. Validação de qualidade dos dados de origem:
`python scripts/dq_check_panorama.py`.

---

_Conteúdo educacional/analítico. Não constitui recomendação de compra ou venda de ativos._
