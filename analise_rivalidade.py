# %% [markdown]
# # AP1 - Rivalidade no setor de carros elétricos (BEV) no Brasil, 2020-2026
#
# Roda com:  python analise_rivalidade.py
# Também abre como notebook no VS Code (células "# %%").
#
# Saídas:
#   graficos/*.png              gráficos para a apresentação
#   resultados/indicadores.csv  HHI, CR1, CR4, nº de marcas por ano
#   resultados/participacao.csv participação de cada marca por ano
#   resultados/resumo.md        texto com os principais achados
#   portal/dados.js             base usada pelo portal (protótipo)
#
# A coluna "status" separa número verificado em fonte pública de número estimado
# pelo grupo. 2024-2026 vêm dos informativos mensais da Fenabrave (coleta_dados.py);
# 2020-2023 por marca ainda são estimativas, porque a Fenabrave não publicava o
# ranking de elétricos nesses anos (conferir no ABVE Data).

# %%
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parent
DADOS, GRAF, RES, PORTAL = (BASE / p for p in ("dados", "graficos", "resultados", "portal"))
for p in (GRAF, RES, PORTAL):
    p.mkdir(exist_ok=True)

plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})
CORES = {"BYD": "#c8102e", "Geely": "#1f5fbf", "Volvo": "#5b7083", "GWM": "#e08a00",
         "BMW": "#3a9ad9", "Mercedes-Benz": "#2b2b2b", "Renault": "#f2c200", "Chevrolet": "#9c6b30",
         "Porsche": "#7a3e9d", "JAC": "#2e8b57", "Nissan": "#888888", "GAC": "#d45087",
         "Zeekr": "#00a0a0", "Outros": "#cfcfcf"}

# %% Carregar dados
marcas = pd.read_csv(DADOS / "emplacamentos_bev_marca.csv")
totais = pd.read_csv(DADOS / "totais_bev.csv")
precos = pd.read_csv(DADOS / "precos.csv")
imposto = pd.read_csv(DADOS / "imposto_importacao.csv")
setores = pd.read_csv(DADOS / "hhi_outros_setores.csv")
eventos = pd.read_csv(DADOS / "eventos.csv")

# Conferência: soma das marcas = total oficial do ano
chk = marcas.groupby("ano")["unidades"].sum().rename("soma").to_frame().join(totais.set_index("ano")["total_bev"])
assert (chk["soma"] == chk["total_bev"]).all(), chk

print("Pontos verificados x estimados:")
print(marcas["status"].value_counts().to_string(), "\n")

# %% Participação de mercado
marcas["share"] = marcas["unidades"] / marcas.groupby("ano")["unidades"].transform("sum") * 100
part = marcas.pivot_table(index="ano", columns="marca", values="share", fill_value=0)
part.round(2).to_csv(RES / "participacao.csv")

# %% Indicadores de concentração
# HHI = soma dos quadrados das participações (%). "Outros" é um grupo de várias
# marcas pequenas, então fica fora da soma (contribuição desprezível).
# Faixas usadas pelo CADE/DOJ: <1500 baixa, 1500-2500 moderada, >2500 alta.
# Grupo econômico (critério do CADE): marcas do mesmo controlador contam como uma só.
GRUPOS = {"Volvo": "Geely Holding", "Zeekr": "Geely Holding", "Geely": "Geely Holding",
          "Mini": "BMW Group", "BMW": "BMW Group", "Porsche": "VW Group", "Audi": "VW Group",
          "Volkswagen": "VW Group", "Denza": "BYD", "GMC": "Chevrolet", "Cadillac": "Chevrolet", "Lexus": "Toyota"}


def indicadores(df):
    s = df[df["marca"] != "Outros"].sort_values("share", ascending=False)["share"]
    sg = df[df["marca"] != "Outros"].assign(g=lambda d: d["marca"].replace(GRUPOS)).groupby("g")["share"].sum()
    return pd.Series({
        "total_bev": int(df["unidades"].sum()),
        "hhi": round((s ** 2).sum()),
        "hhi_grupo": round((sg ** 2).sum()),
        "outros_pct": round(df.loc[df["marca"] == "Outros", "share"].sum(), 1),
        "cr1": round(s.iloc[0], 1),
        "lider": df.loc[df["share"].idxmax(), "marca"],
        "cr4": round(s.iloc[:4].sum(), 1),
        "n_marcas": int((df[(df["marca"] != "Outros")]["unidades"] >= 50).sum()),
        "n_equivalente": round(10000 / (s ** 2).sum(), 1),  # nº de empresas "iguais" que dariam o mesmo HHI
    })

ind = marcas.groupby("ano")[["marca", "unidades", "share"]].apply(indicadores)
# 2026 só vai até outubro: para comparar com anos cheios, anualiza (x 12/10).
meses = totais.set_index("ano")["periodo"].map(lambda p: 10 if p == "jan-out" else 12)
ind["total_anualizado"] = (ind["total_bev"] * 12 / meses).round().astype(int)
ind["crescimento_pct"] = ((ind["total_anualizado"] / ind["total_bev"].shift() - 1) * 100).round(1)
ind["faixa_hhi"] = pd.cut(ind["hhi"], [0, 1500, 2500, 10000], labels=["baixa", "moderada", "alta"])
print(ind.to_string(), "\n")

# Entradas e saídas de marcas (presença com >= 50 unidades).
# Entrada = primeira vez que a marca aparece; reentrada = volta depois de sumir da base
# (em geral é lacuna de dado, não uma saída real do mercado).
pres = marcas[(marcas["marca"] != "Outros") & (marcas["unidades"] >= 50)].groupby("ano")["marca"].apply(set)
entradas, reentradas, saidas, vistas = {}, {}, {}, set(pres.iloc[0])
for a in pres.index[1:]:
    novas = pres[a] - pres[a - 1]
    entradas[int(a)] = sorted(novas - vistas)
    reentradas[int(a)] = sorted(novas & vistas)
    saidas[int(a)] = sorted(pres[a - 1] - pres[a])
    vistas |= pres[a]
print("Entradas por ano:", entradas)
print("Reentradas (provável lacuna de dado):", {a: v for a, v in reentradas.items() if v})
print("Saídas da base:", {a: v for a, v in saidas.items() if v}, "\n")

# Aviso: se "Outros" é maior que marcas listadas, pode esconder marcas relevantes
# (o nº de marcas e as últimas posições do ranking ficam pouco confiáveis).
for a, g in marcas.groupby("ano"):
    o = g.loc[g["marca"] == "Outros", "unidades"].sum()
    menores = g[(g["marca"] != "Outros") & (g["unidades"] < o)]["marca"].tolist()
    if len(menores) > 2:
        print(f"AVISO {a}: 'Outros' ({o}) é maior que {len(menores)} marcas listadas; abrir esse grupo na Fenabrave.")
print()

# Instabilidade de participação (Hymer e Pashigian, 1962): metade da soma das variações
# absolutas de share. 0 = nada mudou; 100 = o mercado trocou inteiro de mãos.
# Diferente da média de posições no ranking, conta também quem entrou e quem saiu.
instab = {int(a): round(float((part.loc[a] - part.loc[a - 1]).abs().sum() / 2), 1) for a in part.index[1:]}
ind["instabilidade_pp"] = pd.Series(instab)
ind.to_csv(RES / "indicadores.csv")
print("Instabilidade de participação (p.p. que trocaram de mãos):", instab, "\n")

# Variação de share (pontos percentuais) entre 2023 e 2026
delta = (part.loc[2026] - part.loc[2023]).sort_values()
print("Ganho/perda de participação 2023 -> 2026 (p.p.):\n", delta.round(1).to_string(), "\n")

# CAGR do mercado
cagr = ((ind.loc[2025, "total_bev"] / ind.loc[2020, "total_bev"]) ** (1 / 5) - 1) * 100

# %% Gráfico 1 - tamanho do mercado
fig, ax = plt.subplots(figsize=(8, 4))
cores = ["#999" if a == 2026 else "#1f5fbf" for a in ind.index]
ax.bar(ind.index.astype(str), ind["total_bev"], color=cores)
for x, v in zip(ind.index.astype(str), ind["total_bev"]):
    ax.text(x, v, f"{v:,.0f}".replace(",", "."), ha="center", va="bottom", fontsize=9)
ax.set_title("Emplacamentos de carros 100% elétricos no Brasil (2026 = jan-out)")
ax.set_ylabel("unidades")
fig.tight_layout(); fig.savefig(GRAF / "01_tamanho_mercado.png"); plt.close(fig)

# %% Gráfico 2 - participação por marca (empilhado)
principais = ["BYD", "Geely", "Volvo", "GWM", "BMW", "Mercedes-Benz", "Renault", "Chevrolet", "Porsche", "JAC", "Nissan"]
p2 = part[principais].copy()
p2["Outros"] = 100 - p2.sum(axis=1)
fig, ax = plt.subplots(figsize=(9, 5))
p2.plot.bar(stacked=True, ax=ax, color=[CORES.get(m, "#aaa") for m in p2.columns], width=0.75)
ax.set_title("Participação de mercado por marca (%)")
ax.set_ylabel("%"); ax.set_xlabel("")
ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", frameon=False)
plt.xticks(rotation=0)
fig.tight_layout(); fig.savefig(GRAF / "02_participacao_marcas.png"); plt.close(fig)

# %% Gráfico 3 - HHI e CR4
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.axhspan(0, 1500, color="#2e8b57", alpha=0.08); ax.axhspan(1500, 2500, color="#e08a00", alpha=0.08)
ax.axhspan(2500, 10000, color="#c8102e", alpha=0.08)
ax.plot(ind.index, ind["hhi"], marker="o", color="#1a1a1a", lw=2, label="HHI")
for a, v in ind["hhi"].items():
    ax.annotate(f"{v:,.0f}".replace(",", "."), (a, v), textcoords="offset points", xytext=(0, -16), ha="center", fontsize=8)
ax.set_ylim(0, 6500); ax.set_ylabel("HHI")
ax.text(2021.5, 300, "baixa (<1.500)", color="#2e8b57", fontsize=8)
ax.text(2021.5, 1650, "moderada", color="#e08a00", fontsize=8)
ax.text(2021.5, 2650, "alta (>2.500)", color="#c8102e", fontsize=8)
ax2 = ax.twinx(); ax2.plot(ind.index, ind["cr4"], ls="--", marker="s", color="#1f5fbf", label="CR4 (%)")
ax2.set_ylim(0, 105); ax2.set_ylabel("CR4 (%)"); ax2.grid(False)
ax.set_title("Concentração: HHI e participação das 4 maiores (CR4)")
fig.legend(loc="lower right", bbox_to_anchor=(0.88, 0.15), frameon=False)
fig.tight_layout(); fig.savefig(GRAF / "03_hhi_cr4.png"); plt.close(fig)

# %% Gráfico 4 - comparação com outros setores
comp = pd.concat([setores[["setor", "hhi"]],
                  pd.DataFrame({"setor": ["Carros elétricos 2022", "Carros elétricos 2026"],
                                "hhi": [ind.loc[2022, "hhi"], ind.loc[2026, "hhi"]]})]).sort_values("hhi")
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(comp["setor"], comp["hhi"], color=["#c8102e" if "elétricos" in s else "#9aa5b1" for s in comp["setor"]])
ax.axvline(1500, color="#e08a00", ls=":"); ax.axvline(2500, color="#c8102e", ls=":")
ax.set_title("HHI do setor x outros setores da economia (referências aproximadas)")
fig.tight_layout(); fig.savefig(GRAF / "04_comparacao_setores.png"); plt.close(fig)

# %% Gráfico 5 - imposto de importação x participação da BYD x Geely
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(part.index, part["BYD"], marker="o", color=CORES["BYD"], label="BYD (% do mercado)")
ax.plot(part.index, part["Geely"], marker="o", color=CORES["Geely"], label="Geely (% do mercado)")
ax.plot(part.index, part["Volvo"], marker="o", color=CORES["Volvo"], label="Volvo (% do mercado)")
# Imposto na data em que cada alíquota entrou em vigor (ano + fração do ano); a participação
# anual é plotada no meio do ano. Antes de 2024 os elétricos eram isentos.
imp_x = [2019.5] + [int(d[:4]) - 0.5 + (int(d[5:]) - 1) / 12 for d in imposto["data"]] + [2026.5]
imp_y = [0] + imposto["aliquota_bev_pct"].tolist() + [imposto["aliquota_bev_pct"].iloc[-1]]
ax.step(imp_x, imp_y, where="post", color="#555", ls="--", label="Imposto de importação BEV (%)")
ax.set_xlim(2019.6, 2026.6)
ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=8)
ax.set_title("Liderança da BYD, entrada da Geely e imposto de importação")
fig.tight_layout(); fig.savefig(GRAF / "05_imposto_lideres.png"); plt.close(fig)

# %% Gráfico 6 - preços de entrada
precos["data"] = pd.to_datetime(precos["data"])
fig, ax = plt.subplots(figsize=(8, 4))
for marca, g in precos.groupby("marca"):
    ax.plot(g["data"], g["preco_brl"] / 1000, marker="o", color=CORES.get(marca, "#888"), label=marca)
    for _, r in g.iterrows():
        ax.annotate(r["modelo"].replace(marca + " ", ""), (r["data"], r["preco_brl"] / 1000),
                    fontsize=7, xytext=(3, 3), textcoords="offset points")
ax.set_ylabel("R$ mil"); ax.legend(frameon=False, fontsize=8)
ax.set_title("Preço de tabela de modelos-chave (R$ mil)")
fig.tight_layout(); fig.savefig(GRAF / "06_precos.png"); plt.close(fig)

# %% Resumo em texto
def br(n):
    return f"{n:,.0f}".replace(",", ".")

l26 = ind.loc[2026]
resumo = f"""# Principais achados

- O mercado de carros 100% elétricos foi de {br(ind.loc[2020,'total_bev'])} unidades em 2020 para {br(ind.loc[2025,'total_bev'])} em 2025 (CAGR de {cagr:.0f}% ao ano). Só de janeiro a outubro de 2026 já são {br(l26['total_bev'])}.
- Até 2022 o mercado era pequeno e disputado por marcas premium importadas (Volvo, Porsche, BMW, Audi, Mercedes). HHI entre {br(ind.loc[2021,'hhi'])} e {br(ind.loc[2022,'hhi'])}, na fronteira entre concentração baixa e moderada (dados desses anos são estimativas do grupo).
- A entrada da BYD em 2023 com preço abaixo de R$ 150 mil mudou o setor. O HHI saltou para {br(ind.loc[2024,'hhi'])} em 2024 e recuou pouco em 2025 ({br(ind.loc[2025,'hhi'])}), com a BYD sozinha em cerca de {ind.loc[2025,'cr1']:.0f}%.
- Em 2026 a Geely ({part.loc[2026,'Geely']:.1f}%) virou a segunda força, e o HHI caiu para {br(l26['hhi'])}. Ainda é alta concentração, mas a rivalidade aumentou. Por grupo econômico (Geely + Volvo + Zeekr), o HHI de 2026 é {br(l26['hhi_grupo'])}.
- 2026 tem só 10 meses: anualizado, o mercado chegaria a cerca de {br(l26['total_anualizado'])} unidades ({l26['crescimento_pct']:.0f}% sobre 2025).
- A rivalidade acontece por preço: Dolphin Mini (R$ 115,8 mil em 2024, R$ 120,0 mil em 2025, R$ 110,0 mil em 2026, valores nominais), Geely EX2 e Renault Kwid E-Tech brigam na faixa de R$ 100-120 mil. As premium (Volvo, BMW, Mercedes, Porsche) perderam participação e ficaram num nicho.
- O imposto de importação subiu de 0% (2023) para 35% (jul/2026). Isso favorece quem produz no Brasil (BYD em Camaçari) e é barreira para novos entrantes que só importam.
- Comparado com outros setores, o elétrico é mais concentrado que o mercado automotivo como um todo (HHI ~1.000) e que os bancos, e passa até telefonia móvel (~3.100) e aviação doméstica (~3.300), setores com só 3 grandes empresas.

Instabilidade de participação (Hymer-Pashigian, p.p. que trocaram de mãos em relação ao ano anterior): {instab}
Entradas de marcas (>= 50 unidades): {entradas}
Reentradas (provável lacuna de dado, conferir): {({a: v for a, v in reentradas.items() if v})}
Limitações: 2020-2023 são estimativas do grupo por marca (ver resultados/av_montecarlo_hhi.csv para a faixa de incerteza). De 2024 em diante os dados são oficiais, mas a Fenabrave só publica as 15 maiores marcas de cada mês: marca pequena que "sai" da base pode só ter caído do ranking.
"""
(RES / "resumo.md").write_text(resumo, encoding="utf-8")
print(resumo)

# %% Exportar base para o portal
portal = {
    "marcas": marcas.drop(columns="share").to_dict("records"),
    "totais": totais.to_dict("records"),
    "precos": precos.assign(data=precos["data"].dt.strftime("%Y-%m")).to_dict("records"),
    "imposto": imposto.to_dict("records"),
    "setores": setores.to_dict("records"),
    "eventos": eventos.to_dict("records"),
}
(PORTAL / "dados.js").write_text("window.DADOS = " + json.dumps(portal, ensure_ascii=False, indent=1) + ";\n",
                                 encoding="utf-8")
print("Arquivos gerados em graficos/, resultados/ e portal/dados.js")
