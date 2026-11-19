# Rivalidade no mercado de carros elétricos no Brasil (AP2)

Portal e análises de concentração e rivalidade entre as marcas de carros 100% elétricos (BEV) no Brasil, 2020 a out/2026.

## Como rodar (Windows)

Precisa de Python 3.9 ou mais novo. No terminal (PowerShell ou Git Bash), dentro da pasta do projeto:

```bash
python -m pip install -r requirements.txt   # uma vez só
python analise_rivalidade.py                # indicadores anuais, gráficos 01 a 06, portal/dados.js
python analise_avancada.py                  # série mensal e modelos estatísticos, gráficos 09 a 18, portal/dados_avancado.js
```

Depois é só abrir `portal/index.html` no navegador (duplo clique). O portal não precisa de servidor; precisa de internet só para carregar a biblioteca de gráficos e as fontes.

Os dados já estão em `dados/`, então **não é preciso rodar a coleta** para apresentar. Para atualizar os dados:

```bash
python coleta_dados.py                 # tudo (a FIPE leva cerca de 40 minutos na 1ª vez)
python coleta_dados.py fenabrave bcb   # só algumas fontes: fenabrave, anual, bcb, comex, fipe
```

A coleta da Fenabrave precisa do programa `pdftotext` (já vem no Git Bash; no PowerShell, instale o poppler ou rode a coleta pelo Git Bash). Depois de coletar, rode as duas análises de novo.

Opcional: `python analise_tam.py respostas.csv` processa o questionário TAM (sem arquivo, usa respostas simuladas; gráficos 07 e 08).

## Estrutura

| Pasta/arquivo | O que é |
|---|---|
| `coleta_dados.py` | baixa os dados públicos e grava os CSVs em `dados/` |
| `analise_rivalidade.py` | **análise principal**: participação, HHI, CR1, CR4, entradas, instabilidade, comparação com outros setores |
| `analise_avancada.py` | série mensal, definição de mercado, Monte Carlo, série interrompida, importações, painel, Bass, FIPE, hedônica, k-means, gradient boosting |
| `portal/index.html` | o portal (abas: Dados e concentração, Análise estratégica, Série mensal e estatística) |
| `graficos/` | gráficos em PNG para slides e relatório |
| `resultados/` | tabelas de saída e os resumos `resumo.md` e `resumo_avancado.md` |
| `relatorio/relatorio.tex` | relatório de 2 páginas (Overleaf) |

## De onde vêm os dados

| Arquivo em `dados/` | Fonte | Situação |
|---|---|---|
| `mensal_bev_marca.csv`, `mensal_hibridos_marca.csv`, `mensal_autos_marca.csv`, `mensal_mercado.csv` | Fenabrave, informativos mensais (jan/2024 a set/2026) | oficial; 15 maiores marcas por mês |
| `mensal_bev_marca.csv`, linhas de out/2026 | Fenabrave ed. 286, reproduzida pelo CarroLens | parcial; só as 5 maiores |
| `emplacamentos_bev_marca.csv`, 2024 a 2026 | soma dos dados mensais acima | oficial |
| `emplacamentos_bev_marca.csv`, 2020 a 2023 | estimativa do grupo por marca; totais da ABVE | **estimado**; conferir no ABVE Data |
| `importacoes_bev.csv` | Comex Stat (MDIC), NCM 8703.80.00 | oficial |
| `macro_mensal.csv` | Banco Central, SGS (séries 20749, 4189, 433, 3698) | oficial |
| `fipe_precos_bev.csv` | Tabela FIPE, preço zero km | oficial |
| `specs_modelos.csv` | potência e bateria de fichas técnicas | **compilado; conferir** |
| `producao_local.csv` | data em que a marca passou a montar no Brasil | **conferir** |
| `precos.csv`, `eventos.csv`, `hhi_outros_setores.csv` | imprensa e referências aproximadas | conferir |

## Dicionário de variáveis

Colunas dos dados:

| Coluna | Significado |
|---|---|
| `ano`, `mes` | período (`mes` no formato AAAA-MM) |
| `marca` | marca comercial; `Outros` = total do período menos as marcas listadas |
| `unidades` | carros emplacados (Fenabrave) ou importados (Comex Stat) |
| `status` | `verificado`/`oficial` (fonte pública), `estimado` (grupo), `calculado` (por diferença), `parcial` |
| `fonte` | de onde saiu cada linha |
| `preco_0km` | preço da Tabela FIPE do carro zero km, R$ nominais |
| `fob_usd` | valor declarado na importação, US$ |
| `aliquota_bev_pct` | imposto de importação sobre elétricos, % |

Indicadores calculados (`resultados/indicadores.csv`):

| Indicador | Definição | Leitura |
|---|---|---|
| participação (share) | unidades da marca ÷ total do período × 100 | |
| HHI | soma dos quadrados das participações (%), sem "Outros" | < 1.500 baixa, 1.500 a 2.500 moderada, > 2.500 alta (CADE/DOJ) |
| HHI por grupo | igual, somando marcas do mesmo controlador (Geely+Volvo+Zeekr etc.) | critério do CADE |
| CR1, CR4 | participação da maior marca e das 4 maiores | |
| empresas equivalentes | 10.000 ÷ HHI | nº de empresas de mesmo tamanho que dariam o mesmo HHI |
| marcas ativas | marcas com 50 ou mais carros no ano | |
| instabilidade | metade da soma das variações absolutas de participação (Hymer-Pashigian) | p.p. do mercado que trocaram de mãos |

## Limitações

- De 2020 a 2023 a Fenabrave não publicava o ranking de elétricos por marca; a incerteza dessas estimativas está em `resultados/av_montecarlo_hhi.csv`.
- A Fenabrave publica só as 15 maiores marcas de elétricos em cada mês; o resto entra em "Outros".
- 2026 vai só até outubro, e outubro tem só as 5 maiores marcas.
- Os gráficos 07 e 08 (TAM) usam respostas simuladas até o questionário ser aplicado.
