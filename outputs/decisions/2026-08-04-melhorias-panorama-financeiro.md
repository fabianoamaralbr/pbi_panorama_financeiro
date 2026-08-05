# Decisão técnica — Melhorias no Panorama Financeiro

**Data:** 2026-08-04
**Agentes:** engineer (execução), analyst (medidas DAX), quality (contratos/DQ)
**Contexto:** revisão do projeto `pbi_panorama_financeiro` — atacar todos os pontos de melhoria levantados.

> **Atualização pós-teste no Desktop (mesma data):** duas mudanças foram **revertidas** —
> (a) o **batching da brapi** (item 1) deixou `d_empresa` vazia porque o plano *free* da brapi
> **não aceita múltiplos tickers por chamada** → voltou para `fnBrapiQuote` (1 req/ticker);
> (b) a **identidade visual navy completa** (itens 9–10) foi revertida a pedido do usuário → a
> aparência voltou ao original (tema padrão, fundo claro, cores/fonte originais nos visuais).
> Permanecem: correção do bug de SUM (medidas dedicadas), clamp 52s, medidas de diagnóstico,
> contratos + validador de DQ, auto date/time off, coluna oculta.

## Mudanças aplicadas

### Modelo semântico (TMDL/M)
1. **Batching brapi** — `fnBrapiQuote` (N+1, ~85 chamadas) → `fnBrapiQuoteLote` (lotes de 20; ~5 chamadas).
   `d_empresa` fatia `IbovTickers` em lotes. Reduz drasticamente refresh e risco de 429.
   *Yahoo (`f_proventos`) permanece 1 chamada/ticker — o endpoint chart não aceita lote (documentado).*
2. **Bug do SUM corrigido (crítico)** — os 4 cards + 4 linhas da p1 apontavam para `Valor Atual`
   **sem filtro de `codigo`** (o `filterConfig` fora removido pelo Desktop), somando TODOS os
   indicadores. Solução robusta: medidas dedicadas `Selic Meta` / `IPCA 12m` / `Dólar PTAX` /
   `PIB Mensal` com `CALCULATE(..., REMOVEFILTERS(d_indicador), d_indicador[codigo]=...)` — filtro
   embutido, imune à remoção de `filterConfig`. Alinhado a [[feedback_dax_performance_first]].
3. **Formato dinâmico (revertido)** — tentou-se `formatStringDefinition` em `Valor Atual`, mas o
   TMDL rejeitou a indentação do bloco (erro ao abrir no Desktop). Revertido para `formatString`
   estático. As unidades heterogêneas ficam corretas via as medidas dedicadas (item 2) + o título
   de cada card; a página "Explorar" usa formato genérico `#,0.00`.
4. **Clamp 52 semanas** — `Posição 52 Semanas` agora limitada a [0,1] (evita >100%/negativo por
   defasagem brapi×Yahoo).
5. **Observabilidade de carga** — medidas de diagnóstico (`Tickers Monitorados`, `Tickers sem Preço`,
   `Cobertura de Preço %`, `Tickers com Proventos`) tornam visíveis falhas parciais silenciosas.
6. **Modelo mais enxuto** — `__PBI_TimeIntelligenceEnabled = 0` (sem hierarquias de data automáticas);
   coluna-lixo `Coluna 1` de `_Medidas` ocultada.

### Qualidade de dados
7. **Contratos** em `contracts/panorama/` (macro + ações) com thresholds de frescor, domínio,
   cobertura e DY plausível (0–30%).
8. **Validador** `scripts/dq_check_panorama.py` — testa dados ao vivo vs contratos, emite relatório
   em `outputs/dq/panorama/` e métricas em `outputs/metrics/`. Validado em 2026-08-04: 7/7 séries
   macro frescas, DYs 2,6%–8,2%. brapi lê `BRAPI_TOKEN` do ambiente (nunca hardcoded).

### Identidade visual (aplicada e depois totalmente revertida)
9. Chegou-se a criar um tema customizado + fundo navy nas 3 páginas e trocar as cores inline dos
   cards/títulos. **Tudo revertido a pedido do dono do projeto**, que optou por não usar qualquer
   identidade de marca aqui (portfólio público). A aparência atual é a original (tema padrão do Power BI).

### Limpeza
11. Slicer de nome-hash `10ad1754b37995964452` → renomeado `v_slicer_empresa` e **removida a seleção
    fixa de 12 empresas + busca "SANEPAR"** (resíduo de dev que filtrava a página inteira).

## Pendências (requerem o usuário / Desktop)
- **Marcar `d_calendario` como Tabela de Data** no Desktop (não expresso em TMDL).
- **Top 15 DY** — aplicar filtro **Top N (15) por `Dividend Yield 12m`** nos visuais da p3 no Desktop.
  O "Top 15" antigo provavelmente vinha da seleção manual removida no item 11; substituir por filtro
  de visual orientado a dados.
- **Validação de refresh** — abrir no Desktop, preencher `BrapiToken`, atualizar e conferir cards/linhas.
  Ao salvar, **zerar `BrapiToken`** antes de commitar.
