# Atalhos do projeto. Uso: make figuras | servir
PY ?= python

.PHONY: figuras servir

figuras:            ## roda as análises: gráficos (PNG e PDF), resultados/ e os dados do site
	$(PY) analise_rivalidade.py
	$(PY) analise_avancada.py

servir:             ## abre o site em http://localhost:8000
	cd portal && python3 -m http.server 8000
