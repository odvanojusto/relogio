import datetime
import json
import sys
import urllib.request


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "relogio-ipad"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


WMO = [
    ((0,), "☀️", "Céu limpo"),
    ((1, 2), "⛅", "Parcialmente nublado"),
    ((3,), "☁️", "Nublado"),
    ((45, 48), "🌫", "Neblina"),
    ((51, 52, 53, 54, 55, 56, 57), "🌦", "Garoa"),
    ((61, 62, 63, 64, 65, 66, 67, 80, 81, 82), "🌧", "Chuva"),
    ((71, 73, 75, 77, 85, 86), "❄️", "Neve"),
    ((95, 96, 99), "⛈", "Tempestade"),
]


def wmo(codigo):
    for codigos, icone, texto in WMO:
        if codigo in codigos:
            return icone, texto
    return "☁️", "Tempo variável"


def icone_texto(t):
    t = t.lower()
    if "trovoada" in t:
        return "⛈"
    if "pancadas" in t or "chuva" in t:
        return "🌧"
    if "garoa" in t:
        return "🌦"
    if "neblina" in t or "nevoeiro" in t:
        return "🌫"
    if "parcialmente" in t or "poucas nuvens" in t:
        return "⛅"
    if "nuvens" in t or "nublado" in t:
        return "☁️"
    return "☀️"


def num(v):
    try:
        return float(v)
    except Exception:
        return None


def inmet_dia(previsao, chave):
    o = previsao.get(chave)
    if not o:
        return None
    mn = mx = None
    texto = ""
    achou = False
    for periodo in ("manha", "tarde", "noite"):
        q = o.get(periodo)
        if not q:
            continue
        achou = True
        a, b = num(q.get("temp_min")), num(q.get("temp_max"))
        if a is not None and (mn is None or a < mn):
            mn = a
        if b is not None and (mx is None or b > mx):
            mx = b
        if q.get("resumo") and (periodo == "tarde" or not texto):
            texto = q["resumo"]
    if not achou and "temp_max" in o:
        mn, mx, texto = num(o.get("temp_min")), num(o.get("temp_max")), o.get("resumo", "")
    if mn is None and mx is None:
        return None
    return {"min": mn, "max": mx, "texto": texto}


def cidade(c):
    url = (
        "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
        "&current_weather=true&daily=weathercode,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max&timezone=auto&forecast_days=2" % (c["lat"], c["lon"])
    )
    om = get(url)
    dd = om["daily"]
    res = {
        "nome": c["nome"],
        "offset": om.get("utc_offset_seconds", 0),
        "agora": round(om["current_weather"]["temperature"]),
        "fonte": "Open-Meteo",
    }
    inmet = None
    if c.get("ibge"):
        try:
            inmet = get("https://apiprevmet3.inmet.gov.br/previsao/%s" % c["ibge"])[c["ibge"]]
        except Exception as e:
            print("INMET indisponível:", e)
    dias = []
    for i in range(2):
        icone, texto = wmo(dd["weathercode"][i])
        dia = {
            "icone": icone,
            "texto": texto,
            "min": round(dd["temperature_2m_min"][i]),
            "max": round(dd["temperature_2m_max"][i]),
            "chuva": dd["precipitation_probability_max"][i],
        }
        if inmet:
            ano, mes, dia_mes = dd["time"][i].split("-")
            x = inmet_dia(inmet, "%s/%s/%s" % (dia_mes, mes, ano))
            if x:
                if x["texto"]:
                    dia["texto"] = x["texto"]
                    dia["icone"] = icone_texto(x["texto"])
                if x["min"] is not None:
                    dia["min"] = round(x["min"])
                if x["max"] is not None:
                    dia["max"] = round(x["max"])
                res["fonte"] = "INMET"
        dias.append(dia)
    res["hoje"], res["amanha"] = dias
    return res


def main():
    with open("cidades.json", encoding="utf-8") as f:
        cidades = json.load(f)
    saida = []
    for c in cidades:
        try:
            saida.append(cidade(c))
        except Exception as e:
            print("Falhou:", c.get("nome"), e)
    if not saida:
        print("Nenhuma cidade atualizada; mantendo o arquivo anterior.")
        sys.exit(0)
    agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open("tempo.json", "w", encoding="utf-8") as f:
        json.dump({"atualizado": agora, "cidades": saida}, f, ensure_ascii=False)


main()
