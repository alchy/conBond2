#!/usr/bin/env python3
"""Učení tvrzeními — dialog, ve kterém se znalost zadává větou.

    python3 scripts/uc.py                    # rozhovor
    python3 scripts/uc.py --davka soubor.txt # po řádcích ze souboru
    python3 scripts/uc.py --ukaz             # co systém ví

Tvary, kterým rozumí:

    román je druh díla              podtřída
    Krakatit je román               instance
    kompatibilita = slučitelnost    synonymum
    Krakatit není báseň             zápor
    ? Krakatit dílo                 dotaz — je Krakatit dílo?
    ?? román                        co všechno román je

Když si mluvnice není jistá, ZEPTÁ SE. „pes je savec" může být podtřída
i instance a hádat je horší než se zeptat: špatná hrana se šíří expanzí dál.

Lemmatizuje se lokálním UDPipe, protože „román je druh díla" má pravou
stranu v genitivu — bez lemmat by z toho byl jiný uzel než „dílo".
"""

import json
import os
import sys
import urllib.parse
import urllib.request

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config  # noqa: E402
from core.tvrzeni import (INSTANCE, PODTRIDA, Mluvnice, Nejasnost,  # noqa: E402
                          Znalost)

ZNALOST = os.path.join(KOREN, "data", "ontology", "tvrzeni.json")
SVAZ = os.path.join(KOREN, "data", "ontology", "typy.json")


def udelej_lemmatizator(url: str):
    """Víceslovný pojem se lemmatizuje po slovech; bez UDPipe se jen zmenší
    písmena, ať se dá pracovat i bez něj."""
    pamet = {}

    def lemmatizuj(text: str) -> str:
        klic = text.strip().lower()
        if not klic:
            return klic
        if klic in pamet:
            return pamet[klic]
        try:
            telo = urllib.parse.urlencode({
                "tokenizer": "", "tagger": "", "data": text}).encode("utf-8")
            with urllib.request.urlopen(url.rstrip("/") + "/process", telo,
                                        timeout=30) as r:
                vysledek = json.loads(r.read().decode("utf-8"))["result"]
            lemmata = []
            for radek in vysledek.splitlines():
                if not radek or radek.startswith("#"):
                    continue
                c = radek.split("\t")
                if len(c) > 3 and c[3] != "PUNCT":
                    lemmata.append(c[2].lower())
            hotovo = " ".join(lemmata) or klic
        except Exception:
            hotovo = klic
        pamet[klic] = hotovo
        return hotovo

    return lemmatizuj


def zpracuj(radek, mluvnice, znalost, ptat_se=True):
    """Jeden řádek vstupu. Vrací text odpovědi."""
    radek = radek.strip()
    if not radek:
        return None

    if radek.startswith("??"):
        pojem = mluvnice._pojem(radek[2:])
        predci = sorted(znalost.predci(pojem))
        if not predci:
            return f"  o „{pojem}\" zatím nic nevím"
        return f"  {pojem} ⊂ " + ", ".join(predci)

    if radek.startswith("?"):
        kusy = radek[1:].split()
        if len(kusy) < 2:
            return "  ptej se ve tvaru: ? Krakatit dílo"
        co = mluvnice._pojem(" ".join(kusy[:-1]))
        cim = mluvnice._pojem(kusy[-1])
        odpoved = znalost.je(co, cim)
        if odpoved is True:
            return f"  ano, {co} je {cim}"
        if odpoved is False:
            return f"  ne, {co} není {cim}"
        return f"  nevím — a mlčení není zápor, jen chybějící znalost"

    vysledek = mluvnice.rozeber(radek)
    if vysledek is None:
        return "  tomuhle tvaru nerozumím (zkus „X je druh Y\" nebo „?\" pro dotaz)"

    if isinstance(vysledek, Nejasnost):
        if not ptat_se:
            return f"  nejasné, přeskakuji: {vysledek.otazka()}"
        print("  " + vysledek.otazka())
        volba = input("  [d]ruh / [k]onkrétní / [p]řeskočit: ").strip().lower()
        if volba.startswith("d"):
            vysledek = vysledek.rozhodni(PODTRIDA)
        elif volba.startswith("k"):
            vysledek = vysledek.rozhodni(INSTANCE)
        else:
            return "  přeskočeno"

    chyba = znalost.prijmi(vysledek)
    if chyba:
        return f"  odmítám: {chyba}"
    znalost.uloz()
    return f"  přijato: {vysledek}"


def main():
    config = Config.nacist()
    mluvnice = Mluvnice(udelej_lemmatizator(config.udpipe))
    znalost = Znalost(ZNALOST)
    ze_svazu = znalost.naplnit_ze_svazu(SVAZ)

    if "--ukaz" in sys.argv:
        print(f"hran ze svazu Wikidat: {ze_svazu}")
        print(f"tvrzení z dialogu:     {len(znalost.tvrzeni)}")
        for t in znalost.tvrzeni:
            print(f"  {t}   ({t.zdroj})")
        print(f"záporů: {len(znalost.zapory)} · synonym: {len(znalost.synonyma)}")
        return 0

    if "--davka" in sys.argv:
        cesta = sys.argv[sys.argv.index("--davka") + 1]
        for radek in open(cesta, encoding="utf-8"):
            if radek.strip():
                print(f"> {radek.strip()}")
                odp = zpracuj(radek, mluvnice, znalost, ptat_se=False)
                if odp:
                    print(odp)
        return 0

    print(f"znalost: {ze_svazu} hran ze svazu, {len(znalost.tvrzeni)} tvrzení")
    print("piš tvrzení, „? X Y\" pro dotaz, „?? X\" pro výpis, Ctrl-D pro konec\n")
    while True:
        try:
            radek = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        odp = zpracuj(radek, mluvnice, znalost)
        if odp:
            print(odp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
