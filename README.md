# Rivalidade no mercado de carros elétricos no Brasil (AP1)

## Como rodar

```bash
pip install -r requirements.txt        # e o programa pdftotext (pacote poppler-utils)
python coleta_dados.py                 # baixa os dados públicos (a FIPE leva cerca de 40 minutos na 1ª vez)
python analise_rivalidade.py           # indicadores anuais, gráficos 01 a 06 e portal/dados.js
python analise_avancada.py             # série mensal e modelos estatísticos, gráficos 09 a 18
python analise_tam.py respostas.csv    # questionário TAM (sem arquivo, usa dados simulados de exemplo)
```

Depois, abrir `portal/index.html` no navegador.

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

## Limitações

- De 2020 a 2023 a Fenabrave não publicava o ranking de elétricos por marca; a incerteza dessas estimativas está em `resultados/av_montecarlo_hhi.csv`.
- A Fenabrave publica só as 15 maiores marcas de elétricos em cada mês; o resto entra em "Outros".
- Os gráficos 07 e 08 (TAM) usam respostas simuladas até o questionário ser aplicado.
