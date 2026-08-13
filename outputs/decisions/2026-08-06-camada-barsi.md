# Registro de Decisão — Camada Barsi

**Data:** 2026-08-06
**Feature:** Camada de análise Barsi (screener preço-teto, consistência, score, simulador)
**Branch:** fabiano
**Status:** implementado

---

## Contexto

Evolução do `pbi_panorama_financeiro` para suportar o método Barsi de seleção de ações
pagadoras de dividendos. A camada adiciona preço-teto (Bazin), consistência de dividendos,
score composto e simulador de renda passiva (bola de neve) sobre um universo BESST ampliado.

---

## Decisões

### (a) Ambiguidade de setor da brapi → override por ticker em `d_besst`

**Problema:** O campo `setor` retornado pela brapi agrupa categorias distintas num mesmo rótulo.
Exemplos: "Finanças e Seguros" cobre bancos e seguradoras; "Utilidade Pública" cobre energia e
saneamento — setores com perfis de dividendos radicalmente diferentes no método Barsi.

**Decisão:** Manter a coluna `setor` (do brapi) em `d_empresa` para uso geral; criar uma
tabela separada `d_besst` com o mapeamento ticker → sigla BESST curado manualmente. O oráculo
Python `scripts/barsi_calc.py` é a fonte de verdade do dicionário `BESST_OVERRIDE`. O merge
acontece em M na partição de `d_empresa`, com fallback para "T" (Telecom) via `setor` e "—"
(fora BESST) para os demais.

**Alternativa descartada:** Tentar inferir BESST só pelo setor da brapi — impreciso demais;
exigiria heurísticas frágeis por nome de empresa.

---

### (b) Teto (preço-teto Bazin) sobre média de 5 anos; consistência em janela de 10 anos

**Problema:** Qual janela temporal usar para cada métrica?

**Decisão:**
- **Preço-teto (Bazin):** média dos últimos 5 anos completos com denominador fixo (penaliza
  anos sem pagamento). Segue a definição canônica do método — 5 anos equilibram
  representatividade e sensibilidade a mudanças recentes.
- **Consistência:** janela de 10 anos (anos pagando, anos consecutivos, cortes, CAGR).
  Janela maior captura ciclos completos e distingue bons pagadores de oportunistas.

As duas janelas coexistem no mesmo modelo porque medem coisas diferentes: teto é um preço
atual; consistência é uma qualidade histórica.

**Alternativa descartada:** Usar a mesma janela (5a) para tudo — perde discriminação de
pagadoras consistentes vs. oportunistas.

---

### (c) Identidade visual definida (tema padrão Power BI)

**Problema:** Definir a identidade visual do relatório. Este projeto é **portfólio público
no GitHub** e o dono decidiu não aplicar nenhuma identidade de marca corporativa.

**Decisão:** Manter o **tema padrão do Power BI** (sem customização de paleta, fonte ou
logomarca). A decisão é do dono do repositório, que optou pelo perfil de portfólio neutro.

**Referência:** Declarado explicitamente no `CLAUDE.md` do projeto ("Sem identidade de marca
neste projeto") e mantido em todas as novas páginas (04 Detalhe, 05 Ranking, 06 Simulador).

---

### (d) `IbovTickers` mantém o nome do parâmetro apesar de virar "universo BESST ampliado"

**Problema:** Após a ampliação, o parâmetro `IbovTickers` passou a incluir tickers fora do
Ibovespa (ABCB4, BMGB4, NEOE3, AESB3, ALUP11, SAPR11, ORVR3, WIZC3, DESK3, FIQE3). O nome
não reflete mais o conteúdo.

**Decisão:** Manter o nome `IbovTickers` para evitar quebrar as referências hardcoded nas
partições M de `d_empresa` e `f_proventos` (ambas leem o parâmetro pelo nome). Renomear
exigiria editar múltiplos arquivos TMDL e uma sessão de atualização no Desktop para
confirmar que as queries refazem a referência corretamente.

**Mitigação:** O `README.md` e o `CLAUDE.md` documentam que o parâmetro passou a representar
o "universo BESST ampliado", não apenas o Ibovespa estrito.

---

### (e) Simulador usa crescimento do aporte (`g`) em vez de crescimento do dividendo

**Problema:** Como modelar o crescimento da renda ao longo do tempo no simulador de bola de
neve — via crescimento do aporte mensal ou via crescimento do dividend yield?

**Decisão:** Parâmetro `p_Sim_CrescAporte` modela o crescimento anual do **aporte mensal**
(g). A fórmula resulta em FV com série geométrica fechada: `Σ A(1+g)^(t-1) × (1+d)^(N-t)`.
Isso evita dupla contagem (crescimento de aporte + crescimento de dividendo seriam
interdependentes) e mantém o resultado verificável contra o oráculo Python
(`scripts/barsi_calc.py::patrimonio_projetado`).

**Alternativa descartada:** Crescimento do DY — exigiria projeção do preço da ação, que
sairia do escopo da análise de renda passiva e introduziria ganho de capital.

---

### (f) Score Barsi — componente P/L

**Problema:** Como mapear o P/L (razão preço/lucro) em pontuação de forma que ações "baratas"
recebam nota máxima e ações caras (ou sem lucro) recebam zero?

**Decisão:** O componente P/L satura em **10 pts para P/L ≤ 5** (bem barato) e cai a 0 em
P/L = 20 (o divisor é 15: `(20 - P/L) / 15 × 10`). Para P/L negativo ou > 20 o componente
é zero. O total do score é limitado ao intervalo `[0, 100]`.

**Implementação:** O oráculo Python (`scripts/barsi_calc.py::score_barsi`) e a medida DAX
`Score Barsi` (em `_Medidas.tmdl`) são mantidos **idênticos** — a fórmula DAX espelha
exatamente a Python. O alinhamento é testado via `test_score_limitado_entre_0_e_100`.

**Pesos completos:** DY Médio 5a 30 pt · Anos Consecutivos 25 pt · BESST 15 pt ·
Margem vs Teto% 20 pt · P/L 10 pt = 100 pt máximo.
