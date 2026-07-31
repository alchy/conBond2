#!/usr/bin/env python3
"""Zásah pole: trefí šablona dotazu tu šablonu, kde odpověď leží?

Metrika je DVOUSTUPŇOVÁ, protože jinak trestá to, co je záměr. Šablona
neidentifikuje jednu odpověď, ale POLE ODPOVĚDI — druh místa, kde odpověď
leží. „Kde se narodil X?" má trefit rodiště u všech autorů naráz; zúžení na
jednoho je až druhý krok, přes entitu.

    zásah pole   je správná faktová šablona MEZI těmi, na které vzor
                 dotazu ukazuje? (tohle dělá aktivační pole)
    zúžení       vybere se v tom poli správná instance? (tohle pole
                 nedělá — je to úloha pro identitu)

Měří se křížově: mapování se staví ze VŠECH otázek kromě té zkoumané, aby
se neměřilo zapamatování.

    python3 scripts/mereni.py
"""

import json
import os
import sys
from collections import Counter, defaultdict

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Pole, UlozisteSouboru, nastavit_log  # noqa: E402

ZLATA = os.path.join(KOREN, "data", "gold", "otazky.json")


def kotva_dotazu(veta):
    """Tázací slovo, jinak kořen — týž výběr jako při skládání otázky."""
    for i, t in enumerate(veta):
        if any(a.startswith("PronType=Int") for a in t["acts"]):
            return i
    for i, t in enumerate(veta):
        if "root" in t["acts"]:
            return i
    return 0


def radky_podle_vety(strana):
    out = {}
    for i, r in enumerate(strana.tok.radky):
        if not r.je_prazdny:
            out[(r.veta, r.poradi_ve_vete)] = i
    return out


def sesbirej(pole, zlata, syrove=False):
    """Dvojice (šablona dotazu, šablona faktu) pro každou otázku ze sady."""
    fakta = pole.uloziste.nacist_korpus("facts")
    rf = radky_podle_vety(pole.fakta)
    rq = radky_podle_vety(pole.dotazy)
    par, ztraceno = [], 0
    for z in zlata:
        veta = fakta[z["veta"]]
        # pořadí v poli je bez interpunkce, zlatá sada indexuje původní větu
        bez = [i for i, t in enumerate(veta) if syrove or t["upos"] != "PUNCT"]
        cil = None
        for j in z["rozsah"]:
            if j in bez:
                cil = rf.get((z["veta"], bez.index(j)))
                if cil is not None:
                    break
        dot = rq.get((z["otazka"], kotva_dotazu_index(pole, z["otazka"])))
        if cil is None or dot is None:
            ztraceno += 1
            continue
        par.append((pole.dotazy.slovo_radku[dot][1],
                    pole.fakta.slovo_radku[cil][1], z))
    return par, ztraceno


def kotva_dotazu_index(pole, qi):
    dotazy = pole.uloziste.nacist_korpus("query")
    if qi >= len(dotazy):
        return 0
    bez = [t for t in dotazy[qi] if t["upos"] != "PUNCT"]
    return kotva_dotazu(bez)


def zmerit(pole, zlata):
    par, ztraceno = sesbirej(pole, zlata)
    if not par:
        return None
    podle = defaultdict(list)
    for qt, ft, _ in par:
        podle[qt].append(ft)

    zasah = zuzeni = neznamy = 0
    for i, (qt, ft, _) in enumerate(par):
        ostatni = [b for j, (a, b, _) in enumerate(par) if a == qt and j != i]
        if not ostatni:
            neznamy += 1
            continue
        if ft in set(ostatni):                 # je cíl v poli odpovědi?
            zasah += 1
        if Counter(ostatni).most_common(1)[0][0] == ft:
            zuzeni += 1
    n = len(par)
    return {"dvojic": n, "ztraceno": ztraceno, "sablon": len(podle),
            "zasah": 100 * zasah / n, "zuzeni": 100 * zuzeni / n,
            "neznamy": 100 * neznamy / n}


def main():
    nastavit_log(uroven="ticho")
    zlata = json.load(open(ZLATA, encoding="utf-8"))
    u = UlozisteSouboru(config=Config.nacist())
    pole = Pole(u)
    print(f"zlatá sada: {len(zlata)} otázek ke spisovatelskému korpusu")
    print("zásah pole = je správný fakt mezi těmi, na které vzor dotazu ukazuje")
    print("zúžení     = je zrovna ten nejčastější (tohle pole dělat nemá)\n")
    print(f"{'r_q':>4} {'r_f':>4} {'dvojic':>7} {'šablon dotazů':>14}"
          f" {'zásah pole':>11} {'zúžení':>8} {'vzor neznámý':>13}")
    print("─" * 68)
    for rq, rf in ((0, 0), (1, 1), (1, 2), (2, 1), (2, 2), (3, 3), (4, 4)):
        pole.nastavit_polomery(rf, rq)
        pole.postavit(vzdy=True)
        v = zmerit(pole, zlata)
        if v is None:
            print(f"{rq:>4} {rf:>4}   žádná dvojice se nenamapovala")
            continue
        print(f"{rq:>4} {rf:>4} {v['dvojic']:>7} {v['sablon']:>14}"
              f" {v['zasah']:>10.0f} % {v['zuzeni']:>7.0f} % {v['neznamy']:>12.0f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
