# Análises avançadas: principais achados

Dados mensais oficiais da Fenabrave (jan/2024 a set/2026; out/2026 parcial), Comex Stat, Banco Central e FIPE.

## 1. Série mensal oficial

Em 33 meses de dados oficiais, o HHI mensal variou de 3.947 (07/2026) a 6.667 (04/2024). A BYD teve o pico de 80,9% em 04/2024 e o piso de 57,4% em 07/2026. A Geely chegou a 24,2% em 07/2026 e recuou para 14,1% em 09/2026 e 8,9% em 10/2026: o desafio à BYD perdeu força nos meses seguintes à alta do imposto para 35% (jul/2026).

## 2. Definição de mercado

Na média de 2026, o HHI é 4.553 se o mercado for só o de elétricos, 2.020 contando híbridos e 916 entre todos os automóveis. A BYD tem 64,1% dos elétricos, 39,7% dos eletrificados e 9,6% de todos os automóveis. Os elétricos passaram de 3,7% para 10,2% dos automóveis emplacados. A conclusão de 'quase monopólio' só vale na definição mais estreita.

## 3. Robustez das estimativas (Monte Carlo)

Com erro de até 30% em cada estimativa, o HHI de 2022 fica entre 1.255 e 1.844: 47% das simulações dão concentração baixa e 53% moderada, então não dá para cravar a faixa de 2022. Já em 2023 a faixa é 3.244 a 3.457, sempre alta. De 2024 em diante os dados são oficiais e não há faixa. A virada de 2023 não depende das estimativas.

## 4. Série temporal interrompida

Controlando a tendência, a chegada em volume do Geely EX2 (nov/2025) está associada a -10,1 p.p. na participação da BYD (p = 0.001, significativo). O degrau de 25% com o início de Camaçari (jul/2025) dá -3,6 p.p. (p = 0.255, não significativo); o imposto de 35% (jul/2026), -4,6 p.p. (p = 0.112, não significativo); o de 18% (jul/2024), 0,3 p.p. (p = 0.933, não significativo). Sem informar data nenhuma, o teste de quebra estrutural aponta 10/2025 (F = 10.8). São 34 meses e eventos próximos entre si: os sinais são confiáveis, os tamanhos nem tanto.

## 5. Importações e estoque (Comex Stat)

Média mensal de importação nos 3 meses antes e nos 3 meses depois de cada alta: 01/2024 (10%): 6.088 antes e 6.458 depois (0,9 vezes); 07/2024 (18%): 16.375 antes e 2.285 depois (7,2 vezes); 07/2025 (25%): 10.739 antes e 1.852 depois (5,8 vezes); 07/2026 (35%): 38.987 antes e 8.595 depois (4,5 vezes). Em 2024 entraram 80.589 carros elétricos e foram emplacados 60.174; em 2025, 68.236 importados para 79.415 emplacados. A China (com Hong Kong) responde por 97% das unidades desde 2024. O valor médio declarado por carro foi de US$ 26.614 em 2023 para US$ 12.818 em 2026. A NCM 8703.80 inclui também veículos elétricos pequenos que não são emplacados como automóvel, então os dois números não fecham um com o outro; o que interessa é o padrão de pico antes e queda depois de cada degrau.

## 6. Painel marca x mês (efeitos fixos de marca e de mês)

Com 13 marcas e 429 observações, cada 10 pontos de imposto estão associados a -32% nas vendas mensais das marcas que só importam, em relação às que montam no Brasil (p = 0.453, erros agrupados por marca). O efeito não é estatisticamente distinguível de zero: os lançamentos de cada marca pesam mais que o imposto no período, e o estoque formado antes de cada alta adia o repasse. A data em que cada marca passou a montar no país está em dados/producao_local.csv e precisa ser conferida.

## 7. Curva de difusão de Bass

De jan/2024 a set/2026 os emplacamentos cresceram em média 5,4% ao mês (dobram a cada 13 meses), e até set/2026 somavam 336.033 carros. Como a curva ainda só acelera, o teto do mercado não pode ser estimado: os três cenários se ajustam igualmente bem aos dados (R² de 0.78, 0.81, 0.81). Com potencial de 2 milhões, o pico de vendas viria em 06/2028 com 41.310 carros por mês. Com potencial de 5 milhões, o pico de vendas viria em 09/2029 com 97.046 carros por mês. Com potencial de 10 milhões, o pico de vendas viria em 07/2030 com 190.260 carros por mês. Em todos, o coeficiente de imitação (q entre 0.076 e 0.083 ao mês) é muito maior que o de inovação (p praticamente zero): a adoção se espalha por contágio, de quem já vê o carro na rua, mais do que por propaganda. Como referência, o mercado inteiro de automóveis emplaca cerca de 192 mil carros por mês, então o cenário de 10 milhões significaria os elétricos tomarem quase todo o mercado até 2030. Para a rivalidade, a leitura de Porter é que a guerra de preços é sustentável enquanto o mercado dobra a cada ano e fica destrutiva quando o pico chegar.

## 8. Preços (FIPE, zero km, corrigidos pelo IPCA)

Entre 01/2024 e 10/2026, nas 11 marcas acompanhadas todo mês, as versões de elétricos zero km na tabela FIPE foram de 27 para 73, e os que custam menos de R$ 150 mil (em valores de hoje), de 0 para 12. O elétrico mais barato caiu de R$ 157.385 para R$ 100.704 em termos reais, e o preço mediano de R$ 294.148 para R$ 229.825.

## 9. Regressão hedônica (preço x características)

Com 68 modelos (R² = 0.87): 10% a mais de potência vale 3,5% no preço e 10% a mais de bateria, 7,8%. Com a mesma potência e a mesma bateria, uma marca chinesa custa -26% (p = 0.000) e uma marca premium 24% (p = 0.002) em relação às demais. Mais baratos do que as características explicam: Volvo EX30 Twin (-39%), Volvo EX30 Core (-34%), Volvo EX40 Ultra AWD (-31%). Mais caros: Porsche Taycan Turbo S (+105%), BMW i7 xDrive60 (+74%), Porsche Macan Turbo (+51%). Potência e bateria foram compiladas de fichas técnicas (dados/specs_modelos.csv) e precisam ser conferidas.

## 10. Grupos estratégicos (k-means)

Entre 3 e 5 grupos, o melhor agrupamento tem 3 (silhueta = 0.47). Grupo 1: 8 modelos, preço mediano de R$ 125 mil, 62% de marcas chinesas (BYD Dolphin Mini, BYD Dolphin, Geely EX2, Chevrolet Spark EUV, JAC e-JS1). Grupo 2: 34 modelos, preço mediano de R$ 232 mil, 59% de marcas chinesas (BYD Dolphin Plus, BYD Yuan Pro, BYD Yuan Plus, GAC Aion ES, GAC Aion Y). Grupo 3: 26 modelos, preço mediano de R$ 543 mil, 27% de marcas chinesas (BYD Seal, BYD Sealion 7, BYD Han, BYD Tan, Chevrolet Equinox EV). É a versão medida do quadro de estratégias genéricas de Porter: mostra em que faixas as marcas chinesas concorrem entre si e onde enfrentam as tradicionais.

## 11. Gradient boosting (painel marca x mês, treino até 2025 e teste em 2026)

Prevendo as vendas mensais de 2026 de cada marca, o modelo completo tem R² = 0.82 fora da amostra, e simplesmente repetir o mês anterior dá 0.80: os dois praticamente empatam, sinal de que as vendas têm muita inércia. Sem a venda do mês anterior, o R² é 0.14 e as variáveis que mais pesam são número de modelos elétricos da marca (0.33), preço de entrada da marca (0.27), preço em relação ao mais barato do mercado (0.11). São só 207 observações de treino e 81 de teste: o exercício serve para ordenar fatores, não para prever.
