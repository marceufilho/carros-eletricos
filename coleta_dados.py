# %% [markdown]
# # Coleta de dados públicos para a análise de rivalidade (carros elétricos, Brasil)
#
# Uso:
#   python coleta_dados.py                 -> coleta tudo
#   python coleta_dados.py fenabrave bcb   -> só as fontes indicadas
#
# Fontes (todas públicas e sem cadastro):
#   fenabrave  Informativo mensal de emplacamentos (PDF). Traz o ranking das 15 maiores
#              marcas de elétricos e de híbridos, mês a mês, a partir de jan/2024.
#   bcb        Banco Central (SGS): juros de financiamento de veículos, Selic, IPCA, câmbio.
#   comex      Comex Stat (MDIC): importações da NCM 8703.80.00 (carros 100% elétricos) por país.
#   fipe       Tabela FIPE: preço do carro zero km dos modelos elétricos, mês a mês.
#
# Os arquivos brutos ficam em dados/brutos/ (cache; não vai para o git). Rodar de novo
# só baixa o que falta. Precisa do programa `pdftotext` (pacote poppler-utils).

# %%
import csv
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
DADOS = BASE / "dados"
BRUTOS = DADOS / "brutos"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-script"}
INICIO, FIM = (2024, 1), (2026, 9)   # primeiro e último informativo Fenabrave com ranking de elétricos
MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
            "setembro", "outubro", "novembro", "dezembro"]


def meses(inicio=INICIO, fim=FIM):
    a, m = inicio
    while (a, m) <= fim:
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def http(url, data=None, headers=None, tentativas=4, espera=2.0):
    """GET/POST com novas tentativas. `data` pode ser dict (form) ou bytes (JSON)."""
    h = dict(UA, **(headers or {}))
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - qualquer falha de rede: espera e tenta de novo
            if i == tentativas - 1:
                raise
            time.sleep(espera * (i + 1) ** 2)


def grava(nome, linhas, colunas):
    with open(DADOS / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        w.writerows(linhas)
    print(f"  {nome}: {len(linhas)} linhas")


# %% ---------------------------------------------------------------- Fenabrave
MARCAS = {"GM": "Chevrolet", "M.BENZ": "Mercedes-Benz", "BYD": "BYD", "GWM": "GWM", "BMW": "BMW", "JAC": "JAC",
          "GAC": "GAC", "MG": "MG", "VW": "Volkswagen", "KIA": "Kia", "RAM": "RAM", "CAOA CHERY": "Caoa Chery",
          "CAOA CHANGAN": "Caoa Changan", "OMODA JAECOO": "Omoda Jaecoo", "OMODA": "Omoda Jaecoo", "LAND ROVER": "Land Rover", "GMC": "GMC"}
CTRL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f]")
LINHA = re.compile(r"([A-Z][A-Z0-9 .&/\-]*?)\s+(\d{1,3}(?:\.\d{3})*)\s+(\d{1,3},\d{1,2}) ?%")
TOTAL = re.compile(r"([AB])\)\s*(?:H.bridos|El.tricos)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)")


def _dec(linha):
    """Algumas páginas (jan/2024) saem do PDF com a fonte deslocada em 29 posições."""
    if not CTRL.search(linha):
        return linha
    return "".join(c if c in " \n\t" else (chr(ord(c) + 29) if ord(c) < 0x7F else " ") for c in linha)


def _marca(nome):
    nome = re.sub(r"^\d+\s*", "", nome).strip()
    return MARCAS.get(nome, nome.title())


def _n(s):
    return int(s.replace(".", ""))


def _pdf_fenabrave(ano, mes):
    pasta = BRUTOS / "fenabrave"
    pasta.mkdir(parents=True, exist_ok=True)
    pdf, txt = pasta / f"{ano}_{mes:02d}.pdf", pasta / f"{ano}_{mes:02d}.txt"
    if not txt.exists():
        if not pdf.exists():
            pdf.write_bytes(http(f"https://www.fenabrave.org.br/portal/files/{ano}_{mes:02d}_02.pdf"))
            time.sleep(0.3)
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
    return [_dec(l) for l in txt.read_text(encoding="utf-8", errors="ignore").replace("\f", "\n").split("\n")]


def _eletrificados(L):
    """Página 'Mercado de Eletrificados Autos': totais e rankings do mês (híbridos à esquerda, elétricos à direita)."""
    i0 = next(i for i, l in enumerate(L) if re.search(r"Eletrificados\s+Autos\s*$", l))
    fim = next((i for i in range(i0 + 5, len(L)) if re.search(r"Eletrificados\s+Comerciais", L[i])), i0 + 70)
    tot, hib, ele, modo = {}, [], [], None
    for l in L[i0:fim]:
        m = TOTAL.search(l)
        if m:
            tot.setdefault(m.group(1), _n(m.group(2)))
        u = l.upper()
        if "TRICOS ACUM" in u:
            break
        if "TRICOS M" in u:
            modo = "mes"
            continue
        if modo:
            for mm in LINHA.finditer(l):
                (hib if mm.start() < 45 else ele).append((_marca(mm.group(1)), _n(mm.group(2)), float(mm.group(3).replace(",", "."))))
    return tot, hib, ele


def _autos(L):
    """Página 'Ranking por marca <mês>': coluna da esquerda = automóveis (todas as motorizações)."""
    i0 = next(i for i, l in enumerate(L) if re.search(r"Ranking por marca [A-Z][a-zç]+/\d{4}", l))
    out = []
    for l in L[i0:i0 + 40]:
        if "COMERCIAIS LEVES" in l and "+" in l:
            break
        mm = LINHA.search(l)
        if mm and mm.start() < 30:
            out.append((_marca(mm.group(1)), _n(mm.group(2)), float(mm.group(3).replace(",", "."))))
    return out


def fenabrave():
    print("Fenabrave: informativos mensais")
    bev, hibr, autos, merc = [], [], [], []
    for ano, mes in meses():
        L = _pdf_fenabrave(ano, mes)
        tot, hib, ele = _eletrificados(L)
        aut = _autos(L)
        ref, fonte = f"{ano}-{mes:02d}", f"Fenabrave, Informativo de {MESES_PT[mes - 1]}/{ano}"
        # total do mês: linha "B) Elétricos"; se a linha não foi lida, deduz da participação da líder
        t_bev = tot.get("B") or round(ele[0][1] / ele[0][2] * 100)
        t_hib = tot.get("A") or round(hib[0][1] / hib[0][2] * 100)
        t_aut = round(sum(u for _, u, _ in aut) / sum(s for _, _, s in aut) * 100)
        for lista, total, destino in ((ele, t_bev, bev), (hib, t_hib, hibr), (aut, t_aut, autos)):
            soma = sum(u for _, u, _ in lista)
            assert 0.85 * total <= soma <= total + 2, (ref, total, soma)
            destino += [{"mes": ref, "marca": m, "unidades": u, "status": "oficial", "fonte": fonte} for m, u, _ in lista]
            destino.append({"mes": ref, "marca": "Outros", "unidades": max(total - soma, 0), "status": "calculado",
                            "fonte": "Total do mês menos as marcas do ranking"})
        merc.append({"mes": ref, "bev": t_bev, "hibridos": t_hib, "autos_total": t_aut})

    # Outubro/2026: o PDF ainda não estava no ar na coleta. As 5 maiores vêm da edição 286 da
    # Fenabrave reproduzida pelo CarroLens (carrolens.com.br/rankings/2026/10); total = BYD / 66,5%.
    out26 = [("BYD", 14292), ("Geely", 1903), ("GWM", 1636), ("Chevrolet", 1037), ("GAC", 966)]
    t = round(14292 / 0.665)
    bev += [{"mes": "2026-10", "marca": m, "unidades": u, "status": "parcial",
             "fonte": "Fenabrave ed. 286 via CarroLens (só as 5 maiores)"} for m, u in out26]
    bev.append({"mes": "2026-10", "marca": "Outros", "unidades": t - sum(u for _, u in out26), "status": "calculado",
                "fonte": "Total estimado (BYD = 66,5%) menos as 5 maiores"})
    merc.append({"mes": "2026-10", "bev": t, "hibridos": "", "autos_total": ""})

    cols = ["mes", "marca", "unidades", "status", "fonte"]
    grava("mensal_bev_marca.csv", bev, cols)
    grava("mensal_hibridos_marca.csv", hibr, cols)
    grava("mensal_autos_marca.csv", autos, cols)
    grava("mensal_mercado.csv", merc, ["mes", "bev", "hibridos", "autos_total"])


# %% ---------------------------------------------------------------- Banco Central
SERIES_BCB = {"juros_veiculos_aa": 20749,   # taxa média de juros, pessoa física, aquisição de veículos (% a.a.)
              "selic_aa": 4189,             # Selic acumulada no mês, anualizada (% a.a.)
              "ipca_mes": 433,              # IPCA, variação mensal (%)
              "cambio_usd": 3698}           # dólar, média mensal de venda (R$)


def bcb():
    print("Banco Central (SGS)")
    tab = {}
    for nome, cod in SERIES_BCB.items():
        url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json"
               "&dataInicial=01/01/2020&dataFinal=31/12/2026")
        for p in json.loads(http(url)):
            d, m, a = p["data"].split("/")
            tab.setdefault(f"{a}-{m}", {})[nome] = p["valor"]
    linhas = [dict(mes=k, **v) for k, v in sorted(tab.items())]
    grava("macro_mensal.csv", linhas, ["mes", *SERIES_BCB])


# %% ---------------------------------------------------------------- Comex Stat
def comex():
    print("Comex Stat: importações NCM 8703.80.00 (veículos só com motor elétrico)")
    # A API exige o detalhe "ncm" para devolver a quantidade em unidades e limita as requisições
    # (HTTP 429): se falhar, esperar um minuto e rodar de novo. O intervalo de meses do período
    # vale para todos os anos, por isso o pedido vai até dezembro.
    corpo = {"flow": "import", "monthDetail": True, "period": {"from": "2020-01", "to": "2026-12"},
             "filters": [{"filter": "ncm", "values": ["87038000"]}], "details": ["country", "ncm"],
             "metrics": ["metricFOB", "metricStatistic", "metricKG"]}
    r = json.loads(http("https://api-comexstat.mdic.gov.br/general", data=json.dumps(corpo).encode(),
                        headers={"Content-Type": "application/json"}))
    linhas = [{"mes": f"{x['year']}-{x['monthNumber']}", "pais": x["country"], "unidades": x["metricStatistic"],
               "fob_usd": x["metricFOB"], "kg": x["metricKG"]} for x in r["data"]["list"]]
    linhas.sort(key=lambda x: (x["mes"], -int(x["unidades"])))
    grava("importacoes_bev.csv", linhas, ["mes", "pais", "unidades", "fob_usd", "kg"])


# %% ---------------------------------------------------------------- FIPE
FIPE = "https://veiculos.fipe.org.br/api/veiculos/"
# Marcas em que todos os modelos são testados (linha quase toda eletrificada) e marcas
# tradicionais, em que só entram modelos com nome de elétrico.
MARCAS_FIPE_TODAS = ["BYD", "GEELY", "GWM", "GAC", "ZEEKR", "JAC", "Leapmotor", "MG", "NETA", "Omoda"]
MARCAS_FIPE_FILTRO = ["Volvo", "Renault", "GM - Chevrolet", "Peugeot", "BMW", "MINI", "Porsche", "Mercedes-Benz",
                      "Audi", "Nissan", "Kia", "Hyundai", "Ford", "Fiat", "CAOA Chery"]
NOME_EV = re.compile(r"el[eé]tr|e-tech|\bev\b|recharge|e-208|e-2008|e-tron|\beq[abces]\b|\bi[x3457]\b|taycan|bolt|"
                     r"spark|captiva|blazer|equinox|leaf|ariya|mach-e|kona|ioniq|500e|megane|icar|ex30|ex40|ec40|ex90|"
                     r"c40|xc40|cooper s?e", re.I)


def _fipe(metodo, **dados):
    cache = BRUTOS / "fipe" / (metodo + "_" + "_".join(str(v) for v in dados.values()) + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    for i in range(6):
        try:
            r = json.loads(http(FIPE + metodo, data=dados or {"x": 1}, headers={"Referer": "https://veiculos.fipe.org.br/"}))
            break
        except Exception:  # noqa: BLE001 - limite de requisições: espera e repete
            time.sleep(20 * (i + 1))
    else:
        raise RuntimeError("FIPE não respondeu")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.25)
    return r


# Marcas acompanhadas todo mês (as que disputam volume). As demais só entram no primeiro e no
# último mês, para o retrato completo do mercado: a FIPE aceita cerca de 50 consultas por minuto.
MARCAS_FIPE_MENSAL = ["BYD", "GEELY", "GWM", "GAC", "ZEEKR", "JAC", "Leapmotor", "MG", "Volvo", "Renault", "GM - Chevrolet"]
NOMES_FIPE = {"GEELY": "Geely", "ZEEKR": "Zeekr", "NETA": "Neta", "MINI": "Mini", "Omoda": "Omoda Jaecoo",
              "CAOA Chery": "Caoa Chery", "GM - Chevrolet": "Chevrolet"}


def fipe(inicio=(2024, 1), fim=(2026, 10)):
    print("FIPE: preço zero km dos modelos elétricos, mês a mês (cerca de 40 minutos na primeira vez)", flush=True)
    refs = {}
    for t in _fipe("ConsultarTabelaDeReferencia"):
        mes, ano = t["Mes"].strip().split("/")
        refs[(int(ano), MESES_PT.index(mes) + 1)] = t["Codigo"]
    linhas, sem_preco = [], set()
    for ano, mes in meses(inicio, fim):
        ref, completo = refs[(ano, mes)], (ano, mes) in (inicio, fim)
        marcas = {m["Label"]: m["Value"] for m in _fipe("ConsultarMarcas", codigoTabelaReferencia=ref, codigoTipoVeiculo=1)}
        for nome in (MARCAS_FIPE_TODAS + MARCAS_FIPE_FILTRO if completo else MARCAS_FIPE_MENSAL):
            if nome not in marcas:
                continue
            mods = _fipe("ConsultarModelos", codigoTabelaReferencia=ref, codigoTipoVeiculo=1, codigoMarca=marcas[nome])
            for md in mods.get("Modelos", []):
                if nome in MARCAS_FIPE_FILTRO and not NOME_EV.search(md["Label"]):
                    continue
                if re.search(r"h[ií]brid|flex|diesel|1\.\d ", md["Label"], re.I):
                    continue
                if (nome, md["Label"]) in sem_preco and not completo:
                    continue   # já consultado sem resultado (não é elétrico); só testa de novo nos meses completos
                v = _fipe("ConsultarValorComTodosParametros", codigoTabelaReferencia=ref, codigoMarca=marcas[nome],
                          codigoModelo=md["Value"], codigoTipoVeiculo=1, anoModelo=32000, codigoTipoCombustivel=4,
                          tipoVeiculo="carro", tipoConsulta="tradicional")
                if "Valor" not in v:
                    sem_preco.add((nome, md["Label"]))
                    continue   # não é elétrico ou não tem zero km nesse mês
                sem_preco.discard((nome, md["Label"]))
                linhas.append({"mes": f"{ano}-{mes:02d}", "marca": NOMES_FIPE.get(nome, nome),
                               "modelo": re.sub(r"\s+", " ", md["Label"]).strip(), "codigo_fipe": v["CodigoFipe"],
                               "preco_0km": int(re.sub(r"\D", "", v["Valor"].split(",")[0])),
                               "cobertura": "todas as marcas" if completo else "marcas principais"})
        print(f"    {ano}-{mes:02d}: {sum(1 for x in linhas if x['mes'] == f'{ano}-{mes:02d}')} modelos", flush=True)
    grava("fipe_precos_bev.csv", linhas, ["mes", "marca", "modelo", "codigo_fipe", "preco_0km", "cobertura"])


# %% ---------------------------------------------------------------- base anual
def anual():
    """Troca as linhas de 2024-2026 da base anual pelas somas dos dados mensais oficiais.

    2020-2023 continuam como estavam (a Fenabrave não publicava ranking de elétricos por marca).
    Marca fora das 15 maiores em algum mês cai em "Outros" naquele mês.
    """
    print("Base anual: 2024-2026 a partir dos dados mensais da Fenabrave")
    with open(DADOS / "mensal_bev_marca.csv", encoding="utf-8") as f:
        mensal = list(csv.DictReader(f))
    soma, parcial = {}, set()
    for r in mensal:
        k = (int(r["mes"][:4]), r["marca"])
        soma[k] = soma.get(k, 0) + int(r["unidades"])
    anos = sorted({a for a, _ in soma})
    arq = DADOS / "emplacamentos_bev_marca.csv"
    with open(arq, encoding="utf-8") as f:
        linhas = [r for r in csv.DictReader(f) if int(r["ano"]) not in anos]
    for (ano, marca), u in sorted(soma.items(), key=lambda kv: (kv[0][0], kv[0][1] == "Outros", -kv[1])):
        per = "jan-out" if ano == 2026 else "jan-dez"
        if marca == "Outros":
            linhas.append({"ano": ano, "marca": marca, "unidades": u, "status": "calculado",
                           "fonte": "Total Fenabrave menos as marcas do ranking mensal (15 maiores; em out/2026, 5 maiores)"})
        else:
            linhas.append({"ano": ano, "marca": marca, "unidades": u, "status": "verificado",
                           "fonte": f"Fenabrave, informativos mensais ({per}/{ano}), soma dos rankings de elétricos (automóveis)"})
    grava("emplacamentos_bev_marca.csv", linhas, ["ano", "marca", "unidades", "status", "fonte"])

    arq = DADOS / "totais_bev.csv"
    with open(arq, encoding="utf-8") as f:
        tot = [r for r in csv.DictReader(f) if int(r["ano"]) not in anos]
    abve = {2024: "61.615", 2025: "80.178"}
    for ano in anos:
        t = sum(u for (a, _), u in soma.items() if a == ano)
        obs = f"; a ABVE, que inclui comerciais leves, divulgou {abve[ano]}" if ano in abve else "; outubro estimado pela participação da BYD"
        tot.append({"ano": ano, "periodo": "jan-out" if ano == 2026 else "ano", "total_bev": t,
                    "status": "parcial" if ano == 2026 else "verificado",
                    "fonte": f"Fenabrave, elétricos (automóveis){obs}"})
    grava("totais_bev.csv", tot, ["ano", "periodo", "total_bev", "status", "fonte"])


# %%
if __name__ == "__main__":
    etapas = {"fenabrave": fenabrave, "anual": anual, "bcb": bcb, "comex": comex, "fipe": fipe}
    for nome in (sys.argv[1:] or etapas):
        etapas[nome]()
