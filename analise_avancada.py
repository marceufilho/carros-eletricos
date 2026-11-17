# %% [markdown]
# # Análises avançadas: série mensal oficial (Fenabrave), importações, preços e modelos
#
# Roda depois de `python coleta_dados.py` e `python analise_rivalidade.py`:
#   python analise_avancada.py
#
# Blocos:
#   1. Concentração mês a mês (HHI, CR4, instabilidade)
#   2. HHI em três definições de mercado: elétricos, eletrificados e todos os automóveis
#   3. Monte Carlo: quanto as estimativas de 2020-2023 mexem no HHI
#   4. Série temporal interrompida: imposto, Geely e produção local na participação da BYD
#   5. Importações (Comex Stat) x emplacamentos: formação de estoque antes do imposto
#   6. Painel marca x mês (diferenças em diferenças): importadoras x quem monta no Brasil
#   7. Curva de difusão de Bass: tamanho potencial do mercado
#   8. Preços FIPE: preço real de entrada e regressão hedônica
#   9. Grupos estratégicos por agrupamento (k-means + PCA)
#  10. Gradient boosting: o que explica as vendas mensais de cada marca
#
# Saídas: graficos/09_*.png em diante, resultados/av_*.csv, resultados/resumo_avancado.md
# e portal/dados_avancado.js.

# %%
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import curve_fit
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score, silhouette_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning)
BASE = Path(__file__).resolve().parent
DADOS, GRAF, RES, PORTAL = (BASE / p for p in ("dados", "graficos", "resultados", "portal"))
plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})
CORES = {"BYD": "#c8102e", "Geely": "#1f5fbf", "Volvo": "#5b7083", "GWM": "#e08a00", "Chevrolet": "#9c6b30",
         "GAC": "#d45087", "Renault": "#f2c200", "Outras": "#b8c0c8"}
rng = np.random.default_rng(42)
ACHADOS = []          # frases para o resumo
PORTAL_OUT = {}       # números para o portal


def br(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def achado(titulo, texto):
    ACHADOS.append((titulo, texto))
    print(f"\n>> {titulo}\n   {texto}")


def salva(fig, nome):
    fig.tight_layout()
    fig.savefig(GRAF / nome)
    fig.savefig((GRAF / nome).with_suffix(".pdf"))   # vetorial, para o artigo e os slides
    plt.close(fig)


# %% Dados
bev = pd.read_csv(DADOS / "mensal_bev_marca.csv")
hib = pd.read_csv(DADOS / "mensal_hibridos_marca.csv")
aut = pd.read_csv(DADOS / "mensal_autos_marca.csv")
merc = pd.read_csv(DADOS / "mensal_mercado.csv")
macro = pd.read_csv(DADOS / "macro_mensal.csv")
imposto = pd.read_csv(DADOS / "imposto_importacao.csv")
anual = pd.read_csv(DADOS / "emplacamentos_bev_marca.csv")
for d in (bev, hib, aut, merc, macro):
    d["data"] = pd.to_datetime(d["mes"] + "-01")

datas = pd.DatetimeIndex(sorted(bev["data"].unique()))
completos = datas[datas <= "2026-09-01"]      # out/2026 só tem as 5 maiores
unid = bev.pivot(index="data", columns="marca", values="unidades").fillna(0)
share = unid.div(unid.sum(axis=1), axis=0) * 100
total = unid.sum(axis=1)

# alíquota em vigor em cada mês
imp = imposto.assign(data=pd.to_datetime(imposto["data"] + "-01")).set_index("data")["aliquota_bev_pct"]
aliq = imp.reindex(datas.union(imp.index)).ffill().fillna(0).reindex(datas)
DEGRAUS = [d for d in imp.index if d in datas and imp[d] > 0 and d > datas[0]]


def linhas_imposto(ax, rotulo=True):
    for d in DEGRAUS:
        ax.axvline(d, color="#555", ls=":", lw=1)
        if rotulo:
            ax.text(d, ax.get_ylim()[1], f" imposto {imp[d]:.0f}%", fontsize=7, va="top", color="#555")


# %% 1. Concentração mês a mês
def hhi(s):
    return float((s.drop("Outros", errors="ignore") ** 2).sum())


ind = pd.DataFrame({
    "total_bev": total.astype(int),
    "hhi": share.apply(hhi, axis=1).round(),
    "cr1": share.drop(columns="Outros").max(axis=1).round(1),
    "cr4": share.drop(columns="Outros").apply(lambda r: r.nlargest(4).sum(), axis=1).round(1),
    "n_marcas_20": (unid.drop(columns="Outros") >= 20).sum(axis=1),
    "instabilidade_pp": (share.diff().abs().sum(axis=1) / 2).round(1),
    "aliquota_pct": aliq,
})
ind.loc[ind.index > completos[-1], ["cr4", "n_marcas_20", "instabilidade_pp"]] = np.nan
ind.index = ind.index.strftime("%Y-%m")
ind.to_csv(RES / "av_indicadores_mensais.csv", index_label="mes")

principais = ["BYD", "Geely", "GWM", "Volvo", "Chevrolet", "GAC"]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True, height_ratios=[3, 2])
for m in principais:
    a1.plot(share.index, share[m], marker="o", ms=3, color=CORES[m], label=m, lw=2 if m in ("BYD", "Geely") else 1.2)
a1.set_ylabel("% dos elétricos emplacados no mês"); a1.legend(ncol=6, frameon=False, fontsize=8, loc="upper center")
a1.set_ylim(0, 95); linhas_imposto(a1)
a1.set_title("Participação mensal por marca (Fenabrave, automóveis 100% elétricos)")
h = share.apply(hhi, axis=1)
a2.plot(h.index, h, color="#1a1a1a", marker="o", ms=3)
a2.axhline(2500, color="#c8102e", ls="--", lw=1); a2.text(datas[0], 2600, "alta concentração (>2.500)", fontsize=7, color="#c8102e")
a2.set_ylabel("HHI"); a2.set_ylim(0, 7000); linhas_imposto(a2, False)
salva(fig, "09_mensal_participacao_hhi.png")

pico = h[completos].idxmax(); vale = h[completos].idxmin()
g = share["Geely"]
achado("Série mensal oficial",
       f"Em {len(completos)} meses completos de dados oficiais ({completos[0]:%m/%Y} a {completos[-1]:%m/%Y}), o HHI mensal variou de {br(h[vale])} ({vale:%m/%Y}) a {br(h[pico])} ({pico:%m/%Y}). "
       f"A BYD teve o pico de {br(share['BYD'].max(), 1)}% em {share['BYD'].idxmax():%m/%Y} e o piso de "
       f"{br(share.loc[completos, 'BYD'].min(), 1)}% em {share.loc[completos, 'BYD'].idxmin():%m/%Y}. "
       f"A Geely chegou a {br(g.max(), 1)}% em {g.idxmax():%m/%Y} e recuou para {br(g.iloc[-2], 1)}% em {g.index[-2]:%m/%Y} "
       f"e {br(g.iloc[-1], 1)}% em {g.index[-1]:%m/%Y}: o desafio à BYD perdeu força nos meses seguintes à alta do imposto para 35% (jul/2026).")
PORTAL_OUT["mensal"] = {"meses": list(ind.index), "hhi": [int(x) for x in ind["hhi"]],
                        "shares": {m: [round(float(x), 1) for x in share[m]] for m in principais},
                        "total": [int(x) for x in ind["total_bev"]], "aliquota": [float(x) for x in aliq]}

# %% 2. Três definições de mercado
def hhi_def(df):
    p = df.pivot(index="data", columns="marca", values="unidades").fillna(0)
    s = p.div(p.sum(axis=1), axis=0) * 100
    return s.drop(columns="Outros").pow(2).sum(axis=1), s

h_bev = h[completos]
elet = pd.concat([bev[bev["data"].isin(completos)], hib]).groupby(["data", "marca"], as_index=False)["unidades"].sum()
h_elet, s_elet = hhi_def(elet)
h_aut, s_aut = hhi_def(aut)
defs = pd.DataFrame({"hhi_eletricos": h_bev, "hhi_eletrificados": h_elet, "hhi_automoveis": h_aut,
                     "byd_eletricos": share.loc[completos, "BYD"], "byd_eletrificados": s_elet["BYD"],
                     "byd_automoveis": s_aut.get("BYD", pd.Series(0, index=completos))}).round(1)
defs["bev_pct_dos_automoveis"] = (merc.set_index("data")["bev"] / merc.set_index("data")["autos_total"] * 100).reindex(completos).round(2)
defs.to_csv(RES / "av_definicoes_mercado.csv", index_label="mes")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
for c, n, cor in (("hhi_eletricos", "Só 100% elétricos", "#c8102e"), ("hhi_eletrificados", "Elétricos + híbridos", "#e08a00"),
                  ("hhi_automoveis", "Todos os automóveis", "#1f5fbf")):
    a1.plot(defs.index, defs[c], color=cor, label=n)
a1.axhline(2500, color="#999", ls="--", lw=1); a1.axhline(1500, color="#999", ls=":", lw=1)
a1.set_title("HHI conforme a definição de mercado"); a1.legend(frameon=False, fontsize=8); a1.set_ylim(0, 7000)
for c, cor in (("byd_eletricos", "#c8102e"), ("byd_eletrificados", "#e08a00"), ("byd_automoveis", "#1f5fbf")):
    a2.plot(defs.index, defs[c], color=cor)
a2.set_title("Participação da BYD em cada definição (%)"); a2.set_ylim(0, 90)
for a in (a1, a2):
    a.tick_params(axis="x", labelrotation=30)
salva(fig, "10_definicoes_mercado.png")

u = defs.loc[defs.index.year == 2026].mean()
achado("Definição de mercado",
       f"Na média de 2026, o HHI é {br(u['hhi_eletricos'])} se o mercado for só o de elétricos, {br(u['hhi_eletrificados'])} "
       f"contando híbridos e {br(u['hhi_automoveis'])} entre todos os automóveis. A BYD tem {br(u['byd_eletricos'], 1)}% dos elétricos, "
       f"{br(u['byd_eletrificados'], 1)}% dos eletrificados e {br(u['byd_automoveis'], 1)}% de todos os automóveis. "
       f"Os elétricos passaram de {br(defs['bev_pct_dos_automoveis'].iloc[0], 1)}% para {br(defs['bev_pct_dos_automoveis'].iloc[-1], 1)}% "
       "dos automóveis emplacados. A conclusão de 'quase monopólio' só vale na definição mais estreita.")
PORTAL_OUT["definicoes"] = {k: round(float(v), 1) for k, v in u.items()}
PORTAL_OUT["definicoes_mensal"] = {"meses": [f"{d:%Y-%m}" for d in defs.index],
                                   **{c: [float(x) for x in defs[c]] for c in defs.columns}}

# %% 3. Monte Carlo sobre as estimativas (2020-2023)
N = 5000
mc = []
for ano, gdf in anual.groupby("ano"):
    est = (gdf["status"] == "estimado").to_numpy()
    fora = (gdf["marca"] == "Outros").to_numpy()
    u0 = gdf["unidades"].to_numpy(float)
    base = (u0[~fora] / u0.sum() * 100) ** 2
    if not est.any():
        mc.append({"ano": ano, "hhi": base.sum(), "p05": base.sum(), "p95": base.sum(), "pct_estimado": 0.0})
        continue
    sims = np.empty(N)
    for i in range(N):
        u_ = u0.copy()
        u_[est] *= rng.uniform(0.7, 1.3, est.sum())                  # cada estimativa erra até 30%
        u_[est] *= u0[est].sum() / u_[est].sum()                     # total do ano fica igual (é dado oficial)
        sims[i] = ((u_[~fora] / u_.sum() * 100) ** 2).sum()
    mc.append({"ano": ano, "hhi": base.sum(), "p05": np.percentile(sims, 5), "p95": np.percentile(sims, 95),
               "pct_estimado": u0[est].sum() / u0.sum() * 100,
               "prob_baixa": (sims < 1500).mean() * 100, "prob_moderada": ((sims >= 1500) & (sims <= 2500)).mean() * 100,
               "prob_alta": (sims > 2500).mean() * 100})
mc = pd.DataFrame(mc).set_index("ano").round(1)
mc.to_csv(RES / "av_montecarlo_hhi.csv")
PORTAL_OUT["montecarlo"] = [{"ano": int(a), "hhi": float(r.hhi), "p05": float(r.p05), "p95": float(r.p95),
                             "pct_estimado": float(r.pct_estimado)} for a, r in mc.iterrows()]

fig, ax = plt.subplots(figsize=(8, 4))
ax.fill_between(mc.index, mc["p05"], mc["p95"], color="#1f5fbf", alpha=0.2, label="faixa de 90% (estimativas com erro de até 30%)")
ax.plot(mc.index, mc["hhi"], marker="o", color="#1a1a1a", label="HHI")
ax.axhline(1500, color="#999", ls=":"); ax.axhline(2500, color="#999", ls="--")
ax.set_ylim(0, 6500); ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("HHI anual e a incerteza das estimativas de 2020 a 2023")
salva(fig, "11_montecarlo_hhi.png")
m22 = mc.loc[2022]
achado("Robustez das estimativas (Monte Carlo)",
       f"Com erro de até 30% em cada estimativa, o HHI de 2022 fica entre {br(m22['p05'])} e {br(m22['p95'])}: "
       f"{br(m22['prob_baixa'])}% das simulações dão concentração baixa e {br(m22['prob_moderada'])}% moderada, então não dá para "
       f"cravar a faixa de 2022. Já em 2023 a faixa é {br(mc.loc[2023, 'p05'])} a {br(mc.loc[2023, 'p95'])}, sempre alta. "
       "De 2024 em diante os dados são oficiais e não há faixa. A virada de 2023 não depende das estimativas.")

# %% 4. Série temporal interrompida (participação da BYD)
y = share.loc[datas, "BYD"]
X = pd.DataFrame({
    "tendencia": np.arange(len(datas)),
    "imposto_18_jul24": (datas >= "2024-07-01").astype(int),
    "imposto_25_camacari_jul25": (datas >= "2025-07-01").astype(int),
    "geely_ex2_nov25": (datas >= "2025-11-01").astype(int),
    "imposto_35_jul26": (datas >= "2026-07-01").astype(int),
}, index=datas)
its = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
its_tab = pd.DataFrame({"coef_pp": its.params, "erro_padrao": its.bse, "p_valor": its.pvalues}).round(3)
its_tab.to_csv(RES / "av_serie_interrompida_byd.csv", index_label="termo")

# Quebra estrutural sem dizer a data: testa cada mês como candidato (sup-F de Quandt-Andrews, quebra no nível)
yc = share.loc[completos, "BYD"]
n = len(yc); t = np.arange(n); sup = []
sq0 = sm.OLS(yc, sm.add_constant(t)).fit().ssr
for k in range(int(n * 0.15), int(n * 0.85)):
    d = (t >= k).astype(int)
    sq1 = sm.OLS(yc, sm.add_constant(np.column_stack([t, d]))).fit().ssr
    sup.append((completos[k], (sq0 - sq1) / (sq1 / (n - 3))))
sup = pd.DataFrame(sup, columns=["mes", "F"]).set_index("mes")
quebra = sup["F"].idxmax()

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(y.index, y, "o-", color=CORES["BYD"], ms=3, label="BYD observado")
ax.plot(y.index, its.fittedvalues, color="#1a1a1a", lw=1.2, label=f"modelo (R² = {its.rsquared:.2f})")
ax.axvline(quebra, color="#1f5fbf", lw=2, alpha=0.4, label=f"quebra mais forte: {quebra:%m/%Y}")
ax.set_ylim(40, 90); linhas_imposto(ax); ax.legend(frameon=False, fontsize=8, loc="lower left")
ax.set_title("Participação da BYD: série temporal interrompida"); ax.set_ylabel("%")
salva(fig, "12_serie_interrompida_byd.png")

c = its_tab["coef_pp"]; p = its_tab["p_valor"]
sig = lambda k: "significativo" if p[k] < 0.05 else ("no limite" if p[k] < 0.10 else "não significativo")
achado("Série temporal interrompida",
       f"Controlando a tendência, a chegada em volume do Geely EX2 (nov/2025) está associada a {br(c['geely_ex2_nov25'], 1)} p.p. na "
       f"participação da BYD (p = {p['geely_ex2_nov25']:.3f}, {sig('geely_ex2_nov25')}). O degrau de 25% com o início de Camaçari (jul/2025) "
       f"dá {br(c['imposto_25_camacari_jul25'], 1)} p.p. (p = {p['imposto_25_camacari_jul25']:.3f}, {sig('imposto_25_camacari_jul25')}); "
       f"o imposto de 35% (jul/2026), {br(c['imposto_35_jul26'], 1)} p.p. (p = {p['imposto_35_jul26']:.3f}, {sig('imposto_35_jul26')}); "
       f"o de 18% (jul/2024), {br(c['imposto_18_jul24'], 1)} p.p. (p = {p['imposto_18_jul24']:.3f}, {sig('imposto_18_jul24')}). "
       f"Sem informar data nenhuma, o teste de quebra estrutural aponta {quebra:%m/%Y} (F = {sup['F'].max():.1f}). "
       f"São {len(datas)} meses (os {len(completos)} completos mais {datas[-1]:%m/%Y}, parcial) e eventos próximos entre si: "
       "os sinais são confiáveis, os tamanhos nem tanto.")
PORTAL_OUT["its"] = {"r2": round(its.rsquared, 2), "quebra": f"{quebra:%m/%Y}",
                     "coef": {k: [round(float(c[k]), 1), round(float(p[k]), 3)] for k in X.columns if k != "tendencia"}}

# %% 5. Importações x emplacamentos (estoque antes do imposto)
impo = pd.read_csv(DADOS / "importacoes_bev.csv")
impo["data"] = pd.to_datetime(impo["mes"] + "-01")
im = impo.groupby("data")[["unidades", "fob_usd"]].sum()
china = impo[impo["pais"].isin(["China", "Hong Kong"])].groupby("data")["unidades"].sum()
im["china_pct"] = (china / im["unidades"] * 100).round(1)
im["fob_medio_usd"] = (im["fob_usd"] / im["unidades"]).round()
cambio = macro.set_index("data")["cambio_usd"]
im["fob_medio_brl"] = (im["fob_medio_usd"] * cambio.reindex(im.index)).round()
im["emplacados"] = total.reindex(im.index)
im.loc[im.index.year < 2024, "emplacados"] = np.nan
im.to_csv(RES / "av_importacoes_mensais.csv", index_label="mes")

jan = im[im.index >= "2023-01-01"]
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(jan.index, jan["unidades"], width=22, color="#9aa5b1", label="importados (Comex Stat, NCM 8703.80)")
ax.plot(jan.index, jan["emplacados"], color=CORES["BYD"], marker="o", ms=3, label="emplacados (Fenabrave)")
for d in imp.index[imp > 0]:
    ax.axvline(d, color="#555", ls=":", lw=1); ax.text(d, ax.get_ylim()[1] * 0.97, f" {imp[d]:.0f}%", fontsize=7, color="#555")
ax.set_ylabel("unidades por mês"); ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("Carros elétricos importados x emplacados: corrida antes de cada alta do imposto")
salva(fig, "13_importacoes_estoque.png")

ev = []
for d in imp.index[imp > 0]:
    antes = im.loc[d - pd.DateOffset(months=3): d - pd.DateOffset(months=1), "unidades"]
    depois = im.loc[d: d + pd.DateOffset(months=2), "unidades"]
    if len(antes) == 3 and len(depois) == 3:
        ev.append({"degrau": f"{d:%m/%Y}", "aliquota": imp[d], "media_3m_antes": antes.mean(), "media_3m_depois": depois.mean(),
                   "razao_antes_depois": antes.mean() / depois.mean(), "pico_mes": antes.idxmax().strftime("%m/%Y"), "pico": antes.max()})
ev = pd.DataFrame(ev).round(2)
ev.to_csv(RES / "av_importacoes_eventos.csv", index=False)
a24 = im.loc["2024"]; a25 = im.loc["2025"]
achado("Importações e estoque (Comex Stat)",
       "Média mensal de importação nos 3 meses antes e nos 3 meses depois de cada alta: "
       + "; ".join(f"{r.degrau} ({r.aliquota:.0f}%): {br(r.media_3m_antes)} antes e {br(r.media_3m_depois)} depois "
                   f"({br(r.razao_antes_depois, 1)} vezes)" for r in ev.itertuples())
       + f". Em 2024 entraram {br(a24['unidades'].sum())} carros elétricos e foram emplacados {br(a24['emplacados'].sum())}; "
       f"em 2025, {br(a25['unidades'].sum())} importados para {br(a25['emplacados'].sum())} emplacados. "
       f"A China (com Hong Kong) responde por {br(china.loc['2024':].sum() / im.loc['2024':, 'unidades'].sum() * 100)}% das unidades desde 2024. "
       f"O valor médio declarado por carro foi de US$ {br(im.loc['2023', 'fob_usd'].sum() / im.loc['2023', 'unidades'].sum())} em 2023 "
       f"para US$ {br(im.loc['2026', 'fob_usd'].sum() / im.loc['2026', 'unidades'].sum())} em 2026. "
       "A NCM 8703.80 inclui também veículos elétricos pequenos que não são emplacados como automóvel, então os dois números "
       "não fecham um com o outro; o que interessa é o padrão de pico antes e queda depois de cada degrau.")
PORTAL_OUT["importacoes"] = {"meses": [f"{d:%Y-%m}" for d in jan.index], "importados": [int(x) for x in jan["unidades"]],
                             "emplacados": [None if pd.isna(x) else int(x) for x in jan["emplacados"]],
                             "eventos": ev.to_dict("records")}

# %% 6. Painel marca x mês: importadoras x quem monta no Brasil
local = pd.read_csv(DADOS / "producao_local.csv")
local["inicio"] = pd.to_datetime(local["inicio"] + "-01")
painel = unid.loc[completos].drop(columns="Outros").stack().rename("unidades").reset_index()
ativos = painel.groupby("marca")["unidades"].apply(lambda s: (s >= 20).sum())
painel = painel[painel["marca"].isin(ativos[ativos >= 12].index)].copy()
ini = local.set_index("marca")["inicio"]
painel["importadora"] = [0 if (m in ini.index and d >= ini[m]) else 1 for m, d in zip(painel["marca"], painel["data"])]
painel["aliquota"] = painel["data"].map(aliq)
painel["exposicao"] = painel["importadora"] * painel["aliquota"]        # só paga o imposto quem importa
painel["ln_unid"] = np.log1p(painel["unidades"])
Xp = pd.concat([painel[["exposicao"]], pd.get_dummies(painel["marca"], prefix="m", drop_first=True, dtype=float),
                pd.get_dummies(painel["data"].dt.strftime("%Y-%m"), prefix="t", drop_first=True, dtype=float)], axis=1)
did = sm.OLS(painel["ln_unid"], sm.add_constant(Xp)).fit(cov_type="cluster", cov_kwds={"groups": painel["marca"].astype("category").cat.codes})
b_did, p_did = did.params["exposicao"], did.pvalues["exposicao"]
pd.DataFrame({"coef": [b_did], "erro_padrao": [did.bse["exposicao"]], "p_valor": [p_did], "n_obs": [len(painel)],
              "n_marcas": [painel["marca"].nunique()], "efeito_10pp_pct": [(np.exp(10 * b_did) - 1) * 100]}).round(4).to_csv(
    RES / "av_painel_imposto.csv", index=False)
PORTAL_OUT["painel"] = {"coef": round(float(b_did), 4), "p": round(float(p_did), 3), "n_obs": int(len(painel)),
                        "n_marcas": int(painel["marca"].nunique()), "efeito_10pp_pct": round(float((np.exp(10 * b_did) - 1) * 100), 1)}
achado("Painel marca x mês (efeitos fixos de marca e de mês)",
       f"Com {painel['marca'].nunique()} marcas e {len(painel)} observações, cada 10 pontos de imposto estão associados a "
       f"{br((np.exp(10 * b_did) - 1) * 100, 0)}% nas vendas mensais das marcas que só importam, em relação às que montam no Brasil "
       f"(p = {p_did:.3f}, erros agrupados por marca). "
       + ("O efeito é estatisticamente distinguível de zero." if p_did < 0.05 else
          "O efeito não é estatisticamente distinguível de zero: os lançamentos de cada marca pesam mais que o imposto no período, "
          "e o estoque formado antes de cada alta adia o repasse.")
       + " A data em que cada marca passou a montar no país está em dados/producao_local.csv e precisa ser conferida.")

# %% 7. Difusão de Bass
ac0 = anual[anual["ano"] < 2024]["unidades"].sum()        # elétricos emplacados antes de 2024
vend = total.loc[completos].to_numpy(float)
acum_ant = ac0 + np.concatenate([[0], np.cumsum(vend)[:-1]])


def bass(N_ant, m, p_, q):
    return (p_ + q * N_ant / m) * (m - N_ant)


# O teto (m) não pode ser estimado enquanto o mercado só acelera: o ajuste livre empurra m para o
# infinito. Por isso o potencial é fixado em três cenários e só p e q são ajustados em cada um.
CENARIOS = {"2 milhões": 2e6, "5 milhões": 5e6, "10 milhões": 10e6}   # carros elétricos acumulados no longo prazo
fut = pd.date_range(completos[-1] + pd.DateOffset(months=1), periods=120, freq="MS")


def projeta(m, p0, q, meses_=120):
    N_, out = ac0 + vend.sum(), []
    for _k in range(meses_):
        s_ = max(bass(N_, m, p0, q), 0); out.append(s_); N_ += s_
    return np.array(out)


bass_tab = []
BASS_CURVAS = {}      # projeção mês a mês de cada cenário, para o portal
fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(completos, vend, "o", ms=3, color=CORES["BYD"], label="emplacados por mês (Fenabrave)")
for (nome, m_), cor in zip(CENARIOS.items(), ("#2e8b57", "#1f5fbf", "#7a3e9d")):
    (p_, q_), _ = curve_fit(lambda N_, p0, q0: bass(N_, m_, p0, q0), acum_ant, vend, p0=[0.0005, 0.08],
                            bounds=([1e-7, 1e-3], [0.05, 1.0]), maxfev=20000)
    aj = bass(acum_ant, m_, p_, q_); proj = projeta(m_, p_, q_)
    r2 = 1 - ((vend - aj) ** 2).sum() / ((vend - vend.mean()) ** 2).sum()
    k = int(np.argmax(proj))
    bass_tab.append({"cenario_m": nome, "p_inovacao": p_, "q_imitacao": q_, "r2": r2, "pico_mes": f"{fut[k]:%m/%Y}",
                     "pico_unidades_mes": proj[k], "vendas_2027": proj[3:15].sum()})
    ax.plot(completos, aj, color=cor, lw=1)
    BASS_CURVAS[nome] = [round(float(x)) for x in proj[:75]]
    ax.plot(fut[:75], proj[:75], color=cor, ls="--", label=f"potencial de {nome}: pico em {fut[k]:%m/%Y}")
ax.set_ylabel("unidades por mês"); ax.legend(frameon=False, fontsize=8)
ax.set_title("Difusão de Bass: três cenários de mercado potencial para os carros elétricos")
salva(fig, "14_bass_difusao.png")
bass_tab = pd.DataFrame(bass_tab)
bass_tab.round(5).to_csv(RES / "av_bass.csv", index=False)
cresc = np.polyfit(np.arange(len(vend)), np.log(vend), 1)[0]      # crescimento médio mensal (log)
b = bass_tab.set_index("cenario_m")
achado("Curva de difusão de Bass",
       f"De jan/2024 a set/2026 os emplacamentos cresceram em média {br((np.exp(cresc) - 1) * 100, 1)}% ao mês (dobram a cada "
       f"{br(np.log(2) / cresc, 0)} meses), e até set/2026 somavam {br(ac0 + vend.sum())} carros. Como a curva ainda só acelera, o teto do mercado "
       "não pode ser estimado: os três cenários se ajustam igualmente bem aos dados (R² de "
       + ", ".join(f"{r.r2:.2f}" for r in bass_tab.itertuples()) + "). "
       + " ".join(f"Com potencial de {nome}, o pico de vendas viria em {r.pico_mes} com {br(r.pico_unidades_mes)} carros por mês." for nome, r in b.iterrows())
       + f" Em todos, o coeficiente de imitação (q entre {b['q_imitacao'].min():.3f} e {b['q_imitacao'].max():.3f} ao mês) é muito maior que o de "
       "inovação (p praticamente zero): a adoção se espalha por contágio, de quem já vê o carro na rua, mais do que por propaganda. "
       f"Como referência, o mercado inteiro de automóveis emplaca cerca de {br(merc['autos_total'].dropna().tail(9).mean() / 1000)} mil carros por mês, "
       "então o cenário de 10 milhões significaria os elétricos tomarem quase todo o mercado até 2030. "
       "Para a rivalidade, a leitura de Porter é que a guerra de preços é sustentável enquanto o mercado dobra a cada ano e fica destrutiva quando o pico chegar.")
PORTAL_OUT["bass"] = bass_tab.round(5).to_dict("records")
PORTAL_OUT["bass_curvas"] = {"meses_obs": [f"{d:%Y-%m}" for d in completos], "vendas": [int(x) for x in vend],
                             "meses_proj": [f"{d:%Y-%m}" for d in fut[:75]], "cenarios": BASS_CURVAS,
                             "crescimento_mes_pct": round(float((np.exp(cresc) - 1) * 100), 1),
                             "meses_para_dobrar": round(float(np.log(2) / cresc)), "acumulado": int(ac0 + vend.sum())}

# %% 8. Preços FIPE: preço real de entrada e regressão hedônica
RES_HED = None
arq_fipe = DADOS / "fipe_precos_bev.csv"
if arq_fipe.exists():
    fipe = pd.read_csv(arq_fipe)
    fipe["data"] = pd.to_datetime(fipe["mes"] + "-01")
    ipca = macro.set_index("data")["ipca_mes"].astype(float).fillna(0)
    indice = (1 + ipca / 100).cumprod()
    base_m = fipe["data"].max()
    defl = (indice.reindex(pd.date_range(indice.index[0], base_m, freq="MS")).ffill().iloc[-1] / indice).reindex(fipe["data"]).to_numpy()
    fipe["preco_real"] = fipe["preco_0km"] * np.nan_to_num(defl, nan=1.0)
    PRINCIPAIS = ["BYD", "Geely", "GWM", "GAC", "Zeekr", "JAC", "Leapmotor", "MG", "Volvo", "Renault", "Chevrolet"]
    retrato = fipe[fipe["data"] == base_m]                         # último mês: todas as marcas
    fipe_tudo, fipe = fipe, fipe[fipe["marca"].isin(PRINCIPAIS)]   # série mensal: só as marcas acompanhadas todo mês
    entrada = fipe.groupby(["data", "marca"])["preco_real"].min().unstack()
    resumo_p = pd.DataFrame({"modelos_a_venda": fipe.groupby("data")["modelo"].nunique(),
                             "marcas": fipe.groupby("data")["marca"].nunique(),
                             "mais_barato_real": fipe.groupby("data")["preco_real"].min().round(),
                             "mediana_real": fipe.groupby("data")["preco_real"].median().round(),
                             "abaixo_150mil": fipe[fipe["preco_real"] < 150000].groupby("data")["modelo"].nunique()}).fillna(0)
    resumo_p.to_csv(RES / "av_precos_fipe_mensal.csv", index_label="mes")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4))
    for m in ["BYD", "Geely", "GWM", "Renault", "Chevrolet", "GAC", "Volvo"]:
        if m in entrada:
            a1.plot(entrada.index, entrada[m] / 1000, color=CORES.get(m, "#888"), label=m)
    a1.set_ylabel(f"R$ mil de {base_m:%m/%Y}"); a1.legend(frameon=False, fontsize=7, ncol=2)
    a1.set_title("Preço real do modelo elétrico mais barato de cada marca (FIPE, zero km)", fontsize=9)
    a2.plot(resumo_p.index, resumo_p["modelos_a_venda"], color="#1a1a1a", label="modelos elétricos à venda")
    a2.plot(resumo_p.index, resumo_p["abaixo_150mil"], color=CORES["BYD"], label="abaixo de R$ 150 mil (real)")
    a2.legend(frameon=False, fontsize=8); a2.set_title("Proliferação de modelos", fontsize=9)
    for a in (a1, a2):
        a.tick_params(axis="x", labelrotation=30)
    salva(fig, "15_precos_fipe.png")
    p0, p1 = resumo_p.iloc[0], resumo_p.iloc[-1]
    achado("Preços (FIPE, zero km, corrigidos pelo IPCA)",
           f"Entre {resumo_p.index[0]:%m/%Y} e {resumo_p.index[-1]:%m/%Y}, nas 11 marcas acompanhadas todo mês, as versões de elétricos zero km na tabela FIPE foram de "
           f"{int(p0['modelos_a_venda'])} para {int(p1['modelos_a_venda'])}, e os que custam menos de R$ 150 mil (em valores de hoje), "
           f"de {int(p0['abaixo_150mil'])} para {int(p1['abaixo_150mil'])}. O elétrico mais barato caiu de R$ {br(p0['mais_barato_real'])} "
           f"para R$ {br(p1['mais_barato_real'])} em termos reais, e o preço mediano de R$ {br(p0['mediana_real'])} para R$ {br(p1['mediana_real'])}.")
    PORTAL_OUT["precos"] = {"meses": [f"{d:%Y-%m}" for d in resumo_p.index], "modelos": [int(x) for x in resumo_p["modelos_a_venda"]],
                            "mais_barato": [int(x) for x in resumo_p["mais_barato_real"]], "mediana": [int(x) for x in resumo_p["mediana_real"]],
                            "abaixo150": [int(x) for x in resumo_p["abaixo_150mil"]]}

    # Regressão hedônica: preço explicado pelas características do carro
    arq_specs = DADOS / "specs_modelos.csv"
    if arq_specs.exists():
        specs = pd.read_csv(arq_specs)
        ult = retrato[["codigo_fipe", "marca", "modelo", "preco_0km"]]
        hed = specs.merge(ult, on="codigo_fipe", how="inner", suffixes=("", "_fipe"))
        hed["ln_preco"] = np.log(hed["preco_0km"])
        hed["ln_bateria"] = np.log(hed["bateria_kwh"]); hed["ln_potencia"] = np.log(hed["potencia_cv"])
        Xh = sm.add_constant(hed[["ln_bateria", "ln_potencia", "marca_chinesa", "marca_premium"]].astype(float))
        hmod = sm.OLS(hed["ln_preco"], Xh).fit(cov_type="HC1")
        hed["residuo_pct"] = (np.exp(hmod.resid) - 1) * 100
        hed["preco_previsto"] = np.exp(hmod.fittedvalues).round()
        hed.sort_values("residuo_pct")[["marca", "modelo", "preco_0km", "preco_previsto", "residuo_pct", "potencia_cv", "bateria_kwh"]].round(1).to_csv(RES / "av_hedonica_modelos.csv", index=False)
        pd.DataFrame({"coef": hmod.params, "erro_padrao": hmod.bse, "p_valor": hmod.pvalues}).round(3).to_csv(
            RES / "av_hedonica_coef.csv", index_label="termo")
        RES_HED = hed
        marca_res = hed.groupby("marca")["residuo_pct"].mean().sort_values()
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.barh(marca_res.index, marca_res.values, color=[CORES.get(m, "#9aa5b1") for m in marca_res.index])
        ax.axvline(0, color="#333", lw=1)
        ax.set_title("Preço acima (+) ou abaixo (-) do que as características do carro explicam, por marca (%)", fontsize=9)
        salva(fig, "16_hedonica_marcas.png")
        hc = hmod.params
        PORTAL_OUT["hedonica"] = {"n": int(len(hed)), "r2": round(float(hmod.rsquared), 2),
                                  "chinesa_pct": round(float((np.exp(hc["marca_chinesa"]) - 1) * 100)),
                                  "premium_pct": round(float((np.exp(hc["marca_premium"]) - 1) * 100)),
                                  "potencia_10_pct": round(float((1.1 ** hc["ln_potencia"] - 1) * 100), 1),
                                  "bateria_10_pct": round(float((1.1 ** hc["ln_bateria"] - 1) * 100), 1),
                                  "marcas": [{"marca": m, "residuo_pct": round(float(v), 1)} for m, v in marca_res.items()]}
        barato = hed.nsmallest(3, "residuo_pct"); caro = hed.nlargest(3, "residuo_pct")
        achado("Regressão hedônica (preço x características)",
               f"Com {len(hed)} modelos (R² = {hmod.rsquared:.2f}): 10% a mais de potência vale {br((1.1 ** hc['ln_potencia'] - 1) * 100, 1)}% no preço e "
               f"10% a mais de bateria, {br((1.1 ** hc['ln_bateria'] - 1) * 100, 1)}%. Com a mesma potência e a mesma bateria, uma marca chinesa custa "
               f"{br((np.exp(hc['marca_chinesa']) - 1) * 100, 0)}% (p = {hmod.pvalues['marca_chinesa']:.3f}) e uma marca premium "
               f"{br((np.exp(hc['marca_premium']) - 1) * 100, 0)}% (p = {hmod.pvalues['marca_premium']:.3f}) em relação às demais. "
               "Mais baratos do que as características explicam: "
               + ", ".join(f"{r.modelo_curto} ({br(r.residuo_pct, 0)}%)" for r in barato.itertuples())
               + ". Mais caros: " + ", ".join(f"{r.modelo_curto} (+{br(r.residuo_pct, 0)}%)" for r in caro.itertuples())
               + ". Potência e bateria foram compiladas de fichas técnicas (dados/specs_modelos.csv) e precisam ser conferidas.")

# %% 9. Grupos estratégicos (k-means + PCA)
if RES_HED is not None:
    hed = RES_HED
    feats = hed[["ln_preco", "ln_potencia", "ln_bateria"]]
    Z = StandardScaler().fit_transform(feats)
    sil = {k: silhouette_score(Z, KMeans(k, n_init=20, random_state=0).fit_predict(Z)) for k in range(3, 6)}   # 2 grupos só separa barato de caro; de 3 a 5 dá grupos úteis
    k_bom = max(sil, key=sil.get)
    km = KMeans(k_bom, n_init=20, random_state=0).fit(Z)
    hed["grupo"] = km.labels_
    ordem = hed.groupby("grupo")["preco_0km"].median().sort_values().index      # numera do mais barato ao mais caro
    hed["grupo"] = hed["grupo"].map({g: i + 1 for i, g in enumerate(ordem)})
    pc = PCA(2).fit(Z); xy = pc.transform(Z)
    perfil = hed.groupby("grupo").agg(modelos=("modelo", "count"), preco_mediano=("preco_0km", "median"),
                                      bateria_media=("bateria_kwh", "mean"), potencia_media=("potencia_cv", "mean"),
                                      pct_chinesas=("marca_chinesa", lambda s: s.mean() * 100),
                                      exemplos=("modelo_curto", lambda s: ", ".join(s.head(5)))).round(0)
    perfil.to_csv(RES / "av_grupos_estrategicos.csv")
    hed[["marca", "modelo_curto", "grupo", "preco_0km", "potencia_cv", "bateria_kwh"]].sort_values(
        ["grupo", "preco_0km"]).to_csv(RES / "av_grupos_modelos.csv", index=False)
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    pal = ["#2e8b57", "#1f5fbf", "#e08a00", "#7a3e9d", "#c8102e", "#555"]
    for gnum in sorted(hed["grupo"].unique()):
        msk = (hed["grupo"] == gnum).to_numpy()
        ax.scatter(xy[msk, 0], xy[msk, 1], s=40, color=pal[gnum - 1],
                   label=f"Grupo {gnum}: mediana R$ {br(perfil.loc[gnum, 'preco_mediano'] / 1000)} mil")
    for (x0, y0), nome in zip(xy, hed["modelo_curto"]):
        ax.annotate(nome, (x0, y0), fontsize=6, xytext=(3, 2), textcoords="offset points")
    ax.set_xlabel(f"Componente 1 ({pc.explained_variance_ratio_[0] * 100:.0f}% da variação)")
    ax.set_ylabel(f"Componente 2 ({pc.explained_variance_ratio_[1] * 100:.0f}%)")
    ax.legend(frameon=False, fontsize=8); ax.set_title("Grupos estratégicos encontrados pelos dados (k-means sobre preço, potência e bateria)", fontsize=9)
    salva(fig, "17_grupos_estrategicos.png")
    achado("Grupos estratégicos (k-means)",
           f"Entre 3 e 5 grupos, o melhor agrupamento tem {k_bom} (silhueta = {sil[k_bom]:.2f}). "
           + " ".join(f"Grupo {gnum}: {int(r.modelos)} modelos, preço mediano de R$ {br(r.preco_mediano / 1000)} mil, "
                      f"{br(r.pct_chinesas)}% de marcas chinesas ({r.exemplos})." for gnum, r in perfil.iterrows())
           + " É a versão medida do quadro de estratégias genéricas de Porter: mostra em que faixas as marcas chinesas concorrem entre si e onde enfrentam as tradicionais.")
    PORTAL_OUT["grupos"] = perfil.reset_index().to_dict("records")

# %% 10. Gradient boosting: o que explica as vendas mensais de cada marca
ml = painel[["data", "marca", "unidades", "ln_unid", "importadora", "aliquota"]].copy()
ml = ml.merge(macro[["data", "juros_veiculos_aa", "cambio_usd"]], on="data", how="left")
ml[["juros_veiculos_aa", "cambio_usd"]] = ml[["juros_veiculos_aa", "cambio_usd"]].astype(float).ffill()
if arq_fipe.exists():
    pm = fipe.groupby(["data", "marca"]).agg(preco_entrada=("preco_real", "min"), n_modelos=("modelo", "nunique")).reset_index()
    ml = ml.merge(pm, on=["data", "marca"], how="left")
    ml["preco_entrada"] = ml.groupby("marca")["preco_entrada"].transform(lambda s: s.ffill().bfill())
    ml["n_modelos"] = ml.groupby("marca")["n_modelos"].transform(lambda s: s.ffill().bfill())
    ml["preco_rel_mercado"] = ml["preco_entrada"] / ml.groupby("data")["preco_entrada"].transform("min")
ml = ml.sort_values(["marca", "data"])
ml["ln_unid_mes_ant"] = ml.groupby("marca")["ln_unid"].shift(1)
ml["meses_no_mercado"] = ml.groupby("marca").cumcount()
ml["marca_chinesa"] = ml["marca"].isin(["BYD", "Geely", "GWM", "GAC", "JAC", "Zeekr", "MG", "Leapmotor", "Omoda Jaecoo", "Neta", "Caoa Chery"]).astype(int)
ml = ml.dropna()
feats_ml = [c for c in ["ln_unid_mes_ant", "preco_entrada", "preco_rel_mercado", "n_modelos", "importadora", "aliquota", "juros_veiculos_aa",
                        "cambio_usd", "meses_no_mercado", "marca_chinesa"] if c in ml]
tr, te = ml[ml["data"] < "2026-01-01"], ml[ml["data"] >= "2026-01-01"]
res_ml = []
for nome, cols in (("com as vendas do mês anterior", feats_ml), ("sem as vendas do mês anterior", [c for c in feats_ml if c != "ln_unid_mes_ant"])):
    gb = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.03, subsample=0.8, random_state=0).fit(tr[cols], tr["ln_unid"])
    r2 = r2_score(te["ln_unid"], gb.predict(te[cols]))
    pi = permutation_importance(gb, te[cols], te["ln_unid"], n_repeats=30, random_state=0)
    res_ml.append((nome, cols, r2, pd.Series(pi.importances_mean, index=cols).sort_values(ascending=False)))
r2_ingenuo = r2_score(te["ln_unid"], te["ln_unid_mes_ant"])
imp_ml = pd.DataFrame({n: s for n, _, _, s in res_ml}).round(3)
imp_ml.to_csv(RES / "av_gradient_boosting_importancia.csv", index_label="variavel")
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4))
for ax, (nome, cols, r2, s) in zip(axs, res_ml):
    ax.barh(s.index[::-1], s.values[::-1], color="#1f5fbf")
    ax.set_title(f"{nome}\nR² fora da amostra (2026) = {r2:.2f}", fontsize=9); ax.tick_params(axis="y", labelsize=8)
fig.suptitle("Gradient boosting: importância por permutação (queda no R² ao embaralhar a variável)", fontsize=9)
salva(fig, "18_gradient_boosting.png")
top_sem = res_ml[1][3].head(3)
NOMES_VAR = {"ln_unid_mes_ant": "vendas do mês anterior", "preco_entrada": "preço de entrada da marca", "preco_rel_mercado": "preço em relação ao mais barato do mercado",
             "n_modelos": "número de modelos elétricos da marca", "importadora": "só importa (não monta no Brasil)", "aliquota": "alíquota do imposto",
             "juros_veiculos_aa": "juros do financiamento", "cambio_usd": "câmbio", "meses_no_mercado": "meses no mercado", "marca_chinesa": "marca chinesa"}
achado("Gradient boosting (painel marca x mês, treino até 2025 e teste em 2026)",
       f"Prevendo as vendas mensais de 2026 de cada marca, o modelo completo tem R² = {res_ml[0][2]:.2f} fora da amostra, e simplesmente repetir "
       f"o mês anterior dá {r2_ingenuo:.2f}: " + ("os dois praticamente empatam, sinal de que as vendas têm muita inércia. " if abs(res_ml[0][2] - r2_ingenuo) < 0.05 else
                                                 "o modelo ganha da regra ingênua. " if res_ml[0][2] > r2_ingenuo else
                                                 "o aprendizado de máquina não ganha da regra ingênua, sinal de que as vendas têm muita inércia. ")
       + f"Sem a venda do mês anterior, o R² é {res_ml[1][2]:.2f} e as variáveis que mais pesam são "
       + ", ".join(f"{NOMES_VAR.get(k, k)} ({v:.2f})" for k, v in top_sem.items())
       + f". São só {len(tr)} observações de treino e {len(te)} de teste: o exercício serve para ordenar fatores, não para prever.")

# %% Resumo e base do portal
txt = "# Análises avançadas: principais achados\n\n" \
      "Dados mensais oficiais da Fenabrave (jan/2024 a set/2026; out/2026 parcial), Comex Stat, Banco Central e FIPE.\n\n"
txt += "\n".join(f"## {i}. {t}\n\n{x}\n" for i, (t, x) in enumerate(ACHADOS, 1))
(RES / "resumo_avancado.md").write_text(txt, encoding="utf-8")
PORTAL_OUT["achados"] = [{"titulo": t, "texto": x} for t, x in ACHADOS]
(PORTAL / "dados_avancado.js").write_text("window.AVANCADO = " + json.dumps(PORTAL_OUT, ensure_ascii=False, indent=1, default=float) + ";\n",
                                          encoding="utf-8")
print("\nArquivos gerados: graficos/09 a 18, resultados/av_*.csv, resultados/resumo_avancado.md, portal/dados_avancado.js")
