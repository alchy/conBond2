#!/usr/bin/env python3
"""Ukázka celé smyčky: věta → šablona → druh tvrzení → znalost → odpověď.

Systém nezná nic. Dostane pár OZNAČENÝCH vět (semínka) a pak věty
NEOZNAČENÉ. Druh nové věty se nehádá z klíčových slov — pozná se podle toho,
se kterým semínkem sdílí šablonu v poli. Přijatá tvrzení jdou do znalosti a
na konci se systému ptáme.

Běží třikrát, aby bylo vidět, co se změnilo. Bez sítka je zápor pro šablonu
neviditelný, protože ho nese spona sama, a to dopadne dvojím způsobem:

  1. Když jsou zaseté kladné i záporné příklady, sejdou se na jedné šabloně
     a ta se stane spornou. Systém pak neřekne nic — ztratí obojí.
  2. Když je zaseté jen kladné, šablona se netváří sporně. Tváří se jistě a
     je vedle: z věty „Máj není román" se systém naučí, že Máj román JE.

Druhý případ je horší, protože není poznat.

    python3 scripts/ukazka.py
"""

import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import Counter

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Pole, UlozisteSouboru, nastavit_log  # noqa: E402
from core.tvrzeni import (INSTANCE, PODTRIDA, SYNONYMUM, ZAPOR,  # noqa: E402
                          Tvrzeni, Znalost)

# Co systém dostane označené. Musí pokrýt TVARY, ne obsah — nová věta se
# zařadí podle šablony, takže semínko a nová věta si musí morfologicky
# odpovídat. Tohle je skutečná podmínka, ne trik ukázky: pole je citlivé na
# rod a pád, takže „Vltava je řeka" nepomůže zařadit „Golem je socha".
SEMINKA = [
    (INSTANCE,  "Krakatit je román."),
    (INSTANCE,  "Hordubal je román."),
    (ZAPOR,     "Krakatit není epos."),
    (ZAPOR,     "Hordubal není epos."),
    (PODTRIDA,  "Román je druh díla."),
    (PODTRIDA,  "Epos je druh díla."),
    (SYNONYMUM, "Kompatibilita je totéž co slučitelnost."),
]

# Co má systém zařadit sám. Tyhle věty nikdo neoznačil.
NOVE = [
    "Máj je epos.",
    "Máj není román.",
    "Bajka je druh díla.",
]

DOTAZY = [
    ("krakatit", "dílo"),   # přes expanzi: román ⊂ dílo
    ("máj", "dílo"),        # totéž, ale přes zařazenou větu
    ("máj", "román"),       # zápor — tohle je to nové
    ("máj", "film"),        # o filmu nepadlo ani slovo
]

ZNACKY = ("druh", "totéž", "totez", "co")


def rozeber(texty, url):
    """Věty na tokeny. Lemma se drží MIMO acts, aby se nedostalo do vektoru
    — do vektoru patří typ, ne hodnota.

    Po jedné větě na dotaz: dávkou je tokenizér občas slepí a čísla vět by
    přestala odpovídat označení. U deseti vět je to laciné a jisté."""
    return [rozeber_vetu(t, url) for t in texty]


def rozeber_vetu(text, url):
    telo = urllib.parse.urlencode({
        "tokenizer": "", "tagger": "", "parser": "",
        "data": text}).encode("utf-8")
    with urllib.request.urlopen(url.rstrip("/") + "/process", telo, timeout=60) as r:
        vysledek = json.loads(r.read().decode("utf-8"))["result"]
    tokeny = []
    for radek in vysledek.splitlines():
        if not radek.strip() or radek.startswith("#"):
            continue
        c = radek.split("\t")
        if len(c) < 8 or "-" in c[0] or "." in c[0]:
            continue
        rysy = [] if c[5] == "_" else c[5].split("|")
        tokeny.append({"form": c[1], "lemma": c[2].lower(), "upos": c[3],
                       "acts": [c[3], c[7]] + rysy})
    return tokeny


def kotva(veta):
    for i, t in enumerate(veta):
        if t["form"].lower() in ("je", "není"):
            return i
    return -1


def strany(veta, i):
    """Pojmy vlevo a vpravo od spony, po lemmatech a bez značek tvaru."""
    def slep(kusy):
        return " ".join(t["lemma"] for t in kusy
                        if t["upos"] != "PUNCT" and t["lemma"] not in ZNACKY)
    return slep(veta[:i]), slep(veta[i + 1:])


def postav_pole(rozebrane, atributy):
    docasna = tempfile.mkdtemp(prefix="pole2-ukazka-")
    os.makedirs(os.path.join(docasna, "corpora"))
    os.makedirs(os.path.join(docasna, "defaults"))
    json.dump(rozebrane, open(os.path.join(docasna, "corpora", "facts.json"), "w"),
              ensure_ascii=False)
    json.dump([], open(os.path.join(docasna, "corpora", "query.json"), "w"))
    shutil.copy(os.path.join(KOREN, "data", "verticals", "verticals.json"),
                os.path.join(docasna, "defaults", "verticals.json"))
    pole = Pole(UlozisteSouboru(config=Config(data=docasna)))
    # r=2, ne 1. Při r=1 splývá „Krakatit je román" s „Román je druh díla",
    # protože UDPipe obě strany označí NOUN Nom Sing Masc a rozlišující
    # genitiv „díla" leží až na offsetu +2. Poloměr tady není kosmetika:
    # rozhoduje, jestli je podtřída od instance vůbec odlišitelná.
    pole.nastavit_polomery(2, 2)
    pole.nastaveni.stred_atributy = atributy
    pole.postavit(vzdy=True)
    return pole, docasna


def sablony_vet(pole, rozebrane):
    """Věta → šablona její spony."""
    radky = {}
    for i, radek in enumerate(pole.fakta.tok.radky):
        if not radek.je_prazdny:
            radky.setdefault(radek.veta, {})[radek.poradi_ve_vete] = i
    out = {}
    for vi, veta in enumerate(rozebrane):
        bez = [t for t in veta if t["upos"] != "PUNCT"]
        i = radky.get(vi, {}).get(kotva(bez))
        if i is not None:
            out[vi] = pole.fakta.slovo_radku[i][1]
    return out


def beh(nazev, atributy, rozebrane, pouzit=None):
    """`pouzit` vybírá, která semínka se použijí — pole se staví ze všech vět
    vždycky, mění se jen to, co systém dostal označené."""
    pouzit = range(len(SEMINKA)) if pouzit is None else pouzit
    print(f"\n{'═' * 72}\n{nazev}\n{'═' * 72}")
    pole, docasna = postav_pole(rozebrane, atributy)
    sablony = sablony_vet(pole, rozebrane)

    # Semínko dá své šabloně druh. Když si na jedné šabloně dvě semínka
    # odporují, šablona druh neurčuje a mlčí — hádat je horší než nevědět.
    hlasy = {}
    for vi in pouzit:
        if vi in sablony:
            hlasy.setdefault(sablony[vi], Counter())[SEMINKA[vi][0]] += 1
    slovnik_sablon = {}
    for t, pocty in hlasy.items():
        if len(pocty) == 1:
            slovnik_sablon[t] = next(iter(pocty))
    print(f"semínek {len(list(pouzit))} → šablon s jednoznačným druhem: "
          f"{len(slovnik_sablon)} z {len(hlasy)}")
    for t, druh in sorted(slovnik_sablon.items()):
        print(f"    {t} = {druh}")
    for t, pocty in sorted(hlasy.items()):
        if len(pocty) > 1:
            print(f"    {t} SPORNÁ {dict(pocty)} — druh neurčuje")

    print("\nzařazení nových vět (nikdo je neoznačil):")
    znalost = Znalost()
    for vi in pouzit:
        l, p = strany(rozebrane[vi], kotva(rozebrane[vi]))
        znalost.prijmi(Tvrzeni(SEMINKA[vi][0], l, p, zdroj="semínko"))

    for j, text in enumerate(NOVE):
        vi = len(SEMINKA) + j
        t = sablony.get(vi)
        druh = slovnik_sablon.get(t)
        if druh is None:
            print(f"    „{text}\"  →  {t}: tenhle tvar neznám, ptám se")
            continue
        l, p = strany(rozebrane[vi], kotva(rozebrane[vi]))
        chyba = znalost.prijmi(Tvrzeni(druh, l, p, zdroj="pole", veta=text))
        znak = {PODTRIDA: "⊂", INSTANCE: "∈", SYNONYMUM: "=", ZAPOR: "≠"}[druh]
        print(f"    „{text}\"  →  {t} = {druh:<9} {l} {znak} {p}"
              + (f"   ODMÍTNUTO: {chyba}" if chyba else ""))

    print("\nodpovědi:")
    for co, cim in DOTAZY:
        odp = znalost.je(co, cim)
        slovy = {True: "ano", False: "NE", None: "nevím"}[odp]
        print(f"    je {co} {cim}?  →  {slovy}")
    shutil.rmtree(docasna, ignore_errors=True)
    return znalost


def main():
    nastavit_log(uroven="ticho")
    vety = [v for _, v in SEMINKA] + list(NOVE)
    rozebrane = rozeber(vety, Config.nacist().udpipe)
    if len(rozebrane) != len(vety):
        print(f"rozbor vrátil {len(rozebrane)} vět místo {len(vety)}, končím")
        return 1
    beh("BEZ SÍTKA — střed mimo vektor (jak to bylo doteď)", (), rozebrane)
    # Nejhorší případ není spor, ale ticho. Když nikdo nezasel záporný
    # příklad, šablona se netváří sporně — tváří se jistě a je vedle.
    bez_zaporu = [i for i, (druh, _) in enumerate(SEMINKA) if druh != ZAPOR]
    beh("BEZ SÍTKA a bez záporných semínek — tichá chyba", (), rozebrane,
        pouzit=bez_zaporu)
    beh("SE SÍTKEM — na střed pustíme Polarity", ("Polarity",), rozebrane)
    return 0


if __name__ == "__main__":
    sys.exit(main())
