#!/usr/bin/env python3
"""Výběr kotev pro ručně psanou zlatou sadu.

Stroj vybere MÍSTA, člověk napíše OTÁZKY. Rozdělení práce podle toho, co
kdo umí líp: agenti spolehlivě najdou, kde v textu leží čas nebo místo a
o kom se ve větě mluví; formulaci otázky ale mechanicky na použitelnou
kvalitu nedotáhneme — ztroskotá to na valenci („Kdy podepsal Olbracht?"
bez předmětu), na směru („Kde odjel" místo „Kam") a na zvratnosti.

    python3 scripts/kotvy.py            # vypíše kandidáty k opsání
    python3 scripts/kotvy.py --json     # totéž strojově

Výběr je vyvážený: po autorech, po typech a bez opakovaných sloves, aby
sada nebyla dvacetkrát „narodil se".
"""

import json
import os
import sys
from collections import defaultdict

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

FAKTA = os.path.join(KOREN, "data", "corpora", "facts.json")
CIL = os.path.join(KOREN, "data", "gold", "_kotvy.json")

# Věta delší než tohle bývá souvětí, kde není jasné, ke které klauzuli
# odpověď patří — a nejasná kotva dělá nejasnou otázku.
MAX_TOKENU = 26
NA_AUTORA = 8


def text_vety(veta):
    return " ".join(t["form"] for t in veta).replace(" .", ".").replace(" ,", ",")


def koren(veta):
    return next((t for t in veta if "root" in t["acts"]
                 and t["upos"] in ("VERB", "AUX")), None)


def entita(t):
    return next((a.split("=", 1)[1] for a in t["acts"] if a.startswith("Ent=")), "")


def vybrat():
    vety = json.load(open(FAKTA, encoding="utf-8"))
    podle_autora = defaultdict(list)
    videna_slovesa = defaultdict(set)

    for vi, veta in enumerate(vety):
        if not (5 <= len(veta) <= MAX_TOKENU):
            continue
        k = koren(veta)
        if k is None:
            continue
        kdo = entita(k)
        if not kdo:
            continue                    # bez známého podmětu nevíme, o kom to je
        for t in veta:
            for n in t.get("navesky", []):
                if n["typ"] not in ("Typ=cas", "Typ=misto"):
                    continue
                sloveso = k["form"].lower()
                if sloveso in videna_slovesa[kdo]:
                    continue            # ať sada není dvacetkrát totéž sloveso
                videna_slovesa[kdo].add(sloveso)
                podle_autora[kdo].append({
                    "veta": vi, "rozsah": n["rozsah"], "typ": n["typ"],
                    "entita": kdo, "sloveso": k["form"],
                    "odpoved": " ".join(veta[j]["form"] for j in n["rozsah"]),
                    "text": text_vety(veta),
                })

    out = []
    for kdo in sorted(podle_autora):
        kandidati = podle_autora[kdo]
        casy = [x for x in kandidati if x["typ"] == "Typ=cas"]
        mista = [x for x in kandidati if x["typ"] == "Typ=misto"]
        # půl na půl, ať sada není jen o datech
        pul = NA_AUTORA // 2
        out.extend(casy[:pul] + mista[:NA_AUTORA - pul])
    return out


def main():
    kotvy = vybrat()
    os.makedirs(os.path.dirname(CIL), exist_ok=True)
    json.dump(kotvy, open(CIL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--json" in sys.argv:
        print(json.dumps(kotvy, ensure_ascii=False, indent=1))
        return 0
    posledni = None
    for i, x in enumerate(kotvy):
        if x["entita"] != posledni:
            posledni = x["entita"]
            print(f"\n── {posledni} " + "─" * (60 - len(posledni)))
        znak = "ČAS " if x["typ"] == "Typ=cas" else "MÍSTO"
        print(f"[{i:>3}] {znak}  odpověď: {x['odpoved']!r}   sloveso: {x['sloveso']}")
        print(f"      {x['text']}")
    print(f"\nkotev celkem: {len(kotvy)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
