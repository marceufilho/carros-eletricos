# %% [markdown]
# # Modelo TAM (Davis, 1989) aplicado à adoção de carros elétricos
#
# Uso:
#   python analise_tam.py                      -> roda com dados de EXEMPLO (simulados)
#   python analise_tam.py dados/respostas.csv  -> roda com as respostas reais da turma
#
# O questionário está em dados/questionario_tam.md.
# Saídas: resultados/tam_*.csv e graficos/07_tam_construtos.png, 08_tam_caminhos.png

# %%
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CONSTRUTOS = {
    "PU": ["PU1", "PU2", "PU3"],          # utilidade percebida
    "PEOU": ["PEOU1", "PEOU2", "PEOU3"],  # facilidade de uso percebida
    "ATT": ["ATT1", "ATT2"],              # atitude
    "BI": ["BI1", "BI2"],                 # intenção de uso
}
NOMES = {"PU": "Utilidade percebida", "PEOU": "Facilidade de uso", "ATT": "Atitude", "BI": "Intenção"}


def dados_exemplo(n=120, seed=7):
    """Respostas SIMULADAS só para testar o script. Não usar como resultado."""
    rng = np.random.default_rng(seed)
    garagem = rng.integers(0, 2, n)
    renda = rng.integers(1, 6, n)
    peou = 2.2 + 0.8 * garagem + rng.normal(0, 0.7, n)          # recarga é o gargalo
    pu = 3.8 + 0.3 * peou - 0.66 + rng.normal(0, 0.6, n)        # utilidade alta
    att = 0.55 * pu + 0.30 * peou + 0.3 + rng.normal(0, 0.5, n)
    bi = 0.35 * att + 0.15 * pu + 0.12 * renda + 0.4 + rng.normal(0, 0.6, n)
    lat = {"PU": pu, "PEOU": peou, "ATT": att, "BI": bi}
    df = pd.DataFrame({"idade": rng.integers(18, 60, n), "renda_faixa": renda, "tem_garagem": garagem})
    for c, itens in CONSTRUTOS.items():
        for it in itens:
            df[it] = np.clip(np.rint(lat[c] + rng.normal(0, 0.45, n)), 1, 5).astype(int)
    return df


def alfa_cronbach(itens: pd.DataFrame) -> float:
    k = itens.shape[1]
    return k / (k - 1) * (1 - itens.var(ddof=1).sum() / itens.sum(axis=1).var(ddof=1))


def ols(y: pd.Series, X: pd.DataFrame):
    """Regressão linear com coeficientes padronizados (betas), t e R²."""
    Xz = (X - X.mean()) / X.std(ddof=1)
    yz = (y - y.mean()) / y.std(ddof=1)
    A = np.column_stack([np.ones(len(Xz)), Xz.values])
    b, *_ = np.linalg.lstsq(A, yz.values, rcond=None)
    res = yz.values - A @ b
    n, k = A.shape
    s2 = res @ res / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ A)))
    r2 = 1 - (res @ res) / ((yz - yz.mean()) ** 2).sum()
    return pd.DataFrame({"beta": b[1:], "t": b[1:] / se[1:]}, index=X.columns), r2


# %%
if len(sys.argv) > 1:
    df = pd.read_csv(sys.argv[1]); origem = sys.argv[1]
else:
    df = dados_exemplo(); origem = "EXEMPLO SIMULADO (substituir pelas respostas reais)"
print("Fonte:", origem, "| respondentes:", len(df), "\n")

# Confiabilidade e escores médios
conf = []
for c, itens in CONSTRUTOS.items():
    df[c] = df[itens].mean(axis=1)
    conf.append({"construto": NOMES[c], "alfa_cronbach": round(alfa_cronbach(df[itens]), 2),
                 "media": round(df[c].mean(), 2), "desvio": round(df[c].std(), 2)})
conf = pd.DataFrame(conf)
print("Confiabilidade (alfa >= 0,7 é aceitável):\n", conf.to_string(index=False), "\n")

# Caminhos do TAM
caminhos = []
for y, xs in [("PU", ["PEOU"]), ("ATT", ["PU", "PEOU"]), ("BI", ["ATT", "PU"])]:
    t, r2 = ols(df[y], df[xs])
    for x, row in t.iterrows():
        caminhos.append({"de": NOMES[x], "para": NOMES[y], "beta": round(row.beta, 2),
                         "t": round(row.t, 1), "significativo_5pct": abs(row.t) > 1.96, "R2_destino": round(r2, 2)})
caminhos = pd.DataFrame(caminhos)
print("Caminhos (betas padronizados):\n", caminhos.to_string(index=False), "\n")

if "tem_garagem" in df:
    g = df.groupby("tem_garagem")[["PEOU", "BI"]].mean().round(2)
    g.index = ["sem garagem", "com garagem"]
    print("Quem tem garagem (pode recarregar em casa):\n", g.to_string(), "\n")

out = BASE / "resultados"; out.mkdir(exist_ok=True)
conf.to_csv(out / "tam_confiabilidade.csv", index=False)
caminhos.to_csv(out / "tam_caminhos.csv", index=False)

# %% Gráficos
gdir = BASE / "graficos"; gdir.mkdir(exist_ok=True)
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.barh(conf["construto"][::-1], conf["media"][::-1], color=["#1f5fbf", "#555", "#e08a00", "#2e8b57"])
ax.axvline(3, color="#999", ls=":"); ax.set_xlim(1, 5)
ax.set_title("Média de cada construto TAM (1 a 5)" + ("" if len(sys.argv) > 1 else " - EXEMPLO"))
fig.tight_layout(); fig.savefig(gdir / "07_tam_construtos.png"); plt.close(fig)

pos = {"Facilidade de uso": (0, 0), "Utilidade percebida": (0, 2), "Atitude": (2, 1), "Intenção": (4, 1)}
fig, ax = plt.subplots(figsize=(8, 3.6)); ax.axis("off")
for nome, (x, y) in pos.items():
    ax.text(x, y, nome, ha="center", va="center", fontsize=10, bbox=dict(boxstyle="round,pad=0.5", fc="#eef2fb", ec="#1f5fbf"))
for _, r in caminhos.iterrows():
    (x1, y1), (x2, y2) = pos[r["de"]], pos[r["para"]]
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", lw=1 + 3 * abs(r["beta"]), color="#2e8b57" if r["significativo_5pct"] else "#bbb",
                                shrinkA=40, shrinkB=40))
    ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, f"β={r['beta']:.2f}".replace(".", ","), ha="center", fontsize=9)
ax.set_xlim(-1, 5); ax.set_ylim(-0.6, 2.6)
ax.set_title("Caminhos do TAM (verde = significativo a 5%)" + ("" if len(sys.argv) > 1 else " - EXEMPLO"))
fig.tight_layout(); fig.savefig(gdir / "08_tam_caminhos.png"); plt.close(fig)
print("Gráficos salvos em graficos/07_tam_construtos.png e 08_tam_caminhos.png")
