# Screenshots do relatório

O GitHub não renderiza `.pbip`. Para o portfólio mostrar o dashboard, exporte as páginas
do Power BI Desktop como PNG e salve **nesta pasta** com os nomes abaixo. Depois, descomente
o bloco de imagens em `README.md` (seção "📸 Prévia").

## Como exportar (Power BI Desktop)

1. Abra `Panorama Financeiro.pbip` e clique em **Atualizar** (para os dados aparecerem).
2. Em cada página, use **Exportar → Imagem** (ou `Win+Shift+S` para recortar a área do canvas).
3. Salve com o nome exato da tabela abaixo, na resolução ~1600×900.

## Arquivos esperados

| Arquivo | Página | Prioridade |
|---|---|---|
| `01-macro.png` | Cenário Macro (KPIs Selic/IPCA/Câmbio/PIB + tendências) | ⭐ essencial |
| `02-explorar.png` | Explorar Indicador | opcional |
| `03-screener.png` | Seleção Barsi (screener preço-teto/score) | ⭐ essencial |
| `04-detalhe.png` | Detalhe da Ação | recomendado |
| `05-ranking.png` | Ranking Barsi | recomendado |
| `06-simulador.png` | Simulador de Renda Passiva | ⭐ essencial |

> Dica: as três marcadas com ⭐ já são o suficiente para a prévia do README. Um GIF curto
> navegando entre as páginas (`docs/img/demo.gif`) também funciona muito bem.
