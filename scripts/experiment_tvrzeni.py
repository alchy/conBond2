#!/usr/bin/env python3
"""Pozná pole druh tvrzení samo, bez mluvnice?

Mluvnice v core/tvrzeni.py je zvláštní parser: hledá v řetězci „je druh",
„není", „=". Kdyby ale tvrzení prošlo POLEM jako každá jiná věta, mohl by
druh vyplynout ze šablony — a učení by se dělo v téže reprezentaci, ve které
systém myslí. Jeden mechanismus místo dvou.

Zkouška je jednoduchá: složit tvrzení všech čtyř druhů s různým obsahem,
prohnat je polem a podívat se, jestli

  1. tvrzení TÉHOŽ druhu sdílejí šablonu (jinak se druh nepozná)
  2. tvrzení RŮZNÝCH druhů mají šablony různé (jinak se pletou)

Kotvou je spona „je" / „není" — kolem ní se ty čtyři tvary liší.

    python3 scripts/experiment_tvrzeni.py
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Pole, UlozisteSouboru, nastavit_log  # noqa: E402

# Obsah se schválně mění, tvar zůstává — testujeme tvar, ne slova.
DVOJICE = [
    ("román", "dílo"), ("báseň", "dílo"), ("socha", "umělecké dílo"),
    ("povídka", "próza"), ("drama", "literatura"), ("esej", "text"),
    ("kočka", "šelma"), ("pes", "savec"), ("dub", "strom"),
    ("kladivo", "nástroj"), ("housle", "nástroj"), ("Praha", "město"),
]
KONKRETNI = [
    ("Krakatit", "román"), ("Máj", "báseň"), ("RUR", "drama"),
    ("Karel Čapek", "spisovatel"), ("Vltava", "řeka"), ("Brno", "město"),
    ("Alfons", "pes"), ("Devětsil", "spolek"), ("Kundera", "autor"),
    ("Seifert", "básník"), ("Praha", "město"), ("Osud", "opera"),
]
SYNONYMA = [
    ("kompatibilita", "slučitelnost"), ("auto", "automobil"),
    ("lékař", "doktor"), ("kniha", "svazek"), ("cesta", "silnice"),
    ("řeč", "jazyk"), ("obchod", "krám"), ("vlak", "souprava"),
]


def vety():
    """Čtyři druhy tvrzení, každý ve svém tvaru."""
    out = []
    for l, p in DVOJICE:
        out.append(("podtrida", f"{l} je druh {p}."))
    for l, p in KONKRETNI:
        out.append(("instance", f"{l} je {p}."))
    for l, p in SYNONYMA:
        out.append(("synonymum", f"{l} je totéž co {p}."))
    for l, p in KONKRETNI[:10]:
        out.append(("zapor", f"{l} není {p}."))
    return out


def rozeber(texty, url):
    telo = urllib.parse.urlencode({
        "tokenizer": "", "tagger": "", "parser": "",
        "data": "\n".join(texty)}).encode("utf-8")
    with urllib.request.urlopen(url.rstrip("/") + "/process", telo, timeout=300) as r:
        vysledek = json.loads(r.read().decode("utf-8"))["result"]
    vety_out, tokeny = [], []
    for radek in vysledek.splitlines():
        if not radek.strip():
            if tokeny:
                vety_out.append(tokeny)
                tokeny = []
            continue
        if radek.startswith("#"):
            continue
        c = radek.split("\t")
        if len(c) < 8 or "-" in c[0] or "." in c[0]:
            continue
        rysy = [] if c[5] == "_" else c[5].split("|")
        tokeny.append({"form": c[1], "upos": c[3], "acts": [c[3], c[7]] + rysy})
    if tokeny:
        vety_out.append(tokeny)
    return vety_out


def kotva(veta):
    """Spona — kolem ní se ty čtyři tvary liší."""
    for i, t in enumerate(veta):
        if t["form"].lower() in ("je", "není"):
            return i
    return 0


def main():
    nastavit_log(uroven="ticho")
    config = Config.nacist()
    znacky = vety()
    print(f"tvrzení: {len(znacky)}  "
          f"({', '.join(f'{k} {v}' for k, v in Counter(d for d, _ in znacky).items())})")

    rozebrane = rozeber([v for _, v in znacky], config.udpipe)
    if len(rozebrane) != len(znacky):
        print(f"  pozor: rozbor vrátil {len(rozebrane)} vět místo {len(znacky)}")
        n = min(len(rozebrane), len(znacky))
        znacky, rozebrane = znacky[:n], rozebrane[:n]

    # pole nad tvrzeními jako nad korpusem
    import shutil
    import tempfile
    docasna = tempfile.mkdtemp(prefix="pole2-tvrzeni-")
    os.makedirs(os.path.join(docasna, "corpora"))
    os.makedirs(os.path.join(docasna, "defaults"))
    json.dump(rozebrane, open(os.path.join(docasna, "corpora", "facts.json"), "w"),
              ensure_ascii=False)
    json.dump([], open(os.path.join(docasna, "corpora", "query.json"), "w"))
    shutil.copy(os.path.join(KOREN, "data", "verticals", "verticals.json"),
                os.path.join(docasna, "defaults", "verticals.json"))

    # Střed má dvě páčky. Mimo = zápor je neviditelný, protože ho nese spona
    # sama. Celý uvnitř = vidí se, ale na faktech to zabije sdílení. Sítko je
    # střední cesta: střed v okně je, projde z něj jen jmenovaný atribut.
    STREDY = [
        ("mimo", False, ()),
        ("celý", True, ()),
        ("Polarity", True, ("Polarity",)),
    ]
    print(f"\n{'r':>2} {'střed':>9} {'šablon':>7} {'čistota':>9} {'rozliš.':>8}   čisté druhy")
    print("─" * 76)
    for jmeno, stred, atributy in STREDY:
      for r in (1, 2, 3):
        pole = Pole(UlozisteSouboru(config=Config(data=docasna)))
        pole.nastavit_polomery(r, r)
        pole.nastaveni.stred_uvnitr = stred
        pole.nastaveni.stred_atributy = atributy
        pole.postavit(vzdy=True)
        f = pole.fakta
        radky = {}
        for i, radek in enumerate(f.tok.radky):
            if not radek.je_prazdny:
                radky.setdefault(radek.veta, {})[radek.poradi_ve_vete] = i

        podle_sablony = defaultdict(list)
        for vi, (druh, _) in enumerate(znacky):
            bez = [t for t in rozebrane[vi] if t["upos"] != "PUNCT"]
            i = radky.get(vi, {}).get(kotva(bez))
            if i is None:
                continue
            podle_sablony[f.slovo_radku[i][1]].append(druh)

        if not podle_sablony:
            print(f"{r:>2}   kotva se nenamapovala")
            continue
        # čistota: kolik tvrzení je ve skupině, kde převažuje jejich druh
        cista = sum(Counter(v).most_common(1)[0][1] for v in podle_sablony.values())
        celkem = sum(len(v) for v in podle_sablony.values())
        # rozlišení: kolik druhů má aspoň jednu vlastní (čistou) šablonu
        vlastni = {v[0] for v in podle_sablony.values() if len(set(v)) == 1}
        print(f"{r:>2} {jmeno:>9} {len(podle_sablony):>7}"
              f" {100*cista/celkem:>8.0f} % {len(vlastni)}/4{'':>5}   "
              f"{', '.join(sorted(vlastni))}")

    print("\ndetail při r=2:")
    pole = Pole(UlozisteSouboru(config=Config(data=docasna)))
    pole.nastavit_polomery(2, 2)
    pole.postavit(vzdy=True)
    f = pole.fakta
    radky = {}
    for i, radek in enumerate(f.tok.radky):
        if not radek.je_prazdny:
            radky.setdefault(radek.veta, {})[radek.poradi_ve_vete] = i
    podle = defaultdict(list)
    for vi, (druh, veta) in enumerate(znacky):
        bez = [t for t in rozebrane[vi] if t["upos"] != "PUNCT"]
        i = radky.get(vi, {}).get(kotva(bez))
        if i is not None:
            podle[f.slovo_radku[i][1]].append((druh, veta))
    for t, cleny in sorted(podle.items(), key=lambda x: -len(x[1]))[:6]:
        druhy = Counter(d for d, _ in cleny)
        print(f"  {t}  {len(cleny)}×  {dict(druhy)}")
        print(f"       „{cleny[0][1]}\"")
    shutil.rmtree(docasna, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
