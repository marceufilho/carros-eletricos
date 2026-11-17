# Atalhos do projeto. Uso: make figuras | artigo | slides | site | servir | limpar
PY ?= python
LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error

.PHONY: figuras artigo slides site servir limpar

figuras:            ## roda as análises: gráficos (PNG e PDF), resultados/ e os dados do site
	$(PY) analise_rivalidade.py
	$(PY) analise_avancada.py

artigo:             ## artigo/artigo.pdf
	cd artigo && $(LATEXMK) artigo.tex

slides:             ## slides/slides.pdf
	cd slides && $(LATEXMK) slides.tex

site: artigo slides ## copia os PDFs para dentro do site
	cp artigo/artigo.pdf slides/slides.pdf portal/

servir:             ## abre o site em http://localhost:8000
	cd portal && python3 -m http.server 8000

limpar:
	cd artigo && latexmk -C artigo.tex
	cd slides && latexmk -C slides.tex
	rm -f portal/artigo.pdf portal/slides.pdf
