#!/usr/bin/env python3
"""Články z české Wikipedie do data/raw/ — jediné místo, kde jde ven ze stroje.

    python3 scripts/stahni_wiki.py            # stáhne, co ještě není
    python3 scripts/stahni_wiki.py --seznam   # jen vypíše, co by stáhl
    python3 scripts/stahni_wiki.py --znovu    # přepíše i to, co už je

PROČ VÍC AUTORŮ. Dvanáct článků dalo 3478 vět, ale entita je jen u 15 % z nich
a otázky se dají klást jen na tu čtvrtinu. Víc autorů zvětší hlavně to, co je
na měření podstatné: kolik tvarů a vzorů se opakuje NAPŘÍČ články. Jeden
článek navíc přidá pár set vět, ale ověří tisíce už existujících šablon.

LICENCE. Wikipedie je CC BY-SA 4.0. Texty jsou tu jako baseline korpus pro
měření, ne jako obsah projektu — viz data/raw/ZDROJ.md.

STAHUJE SE SLUŠNĚ: jeden článek za dotaz, pauza mezi nimi, vlastní
User-Agent. Kdo už soubor má, ten se přeskočí.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core.log import log, nastavit  # noqa: E402

SUROVE = os.path.join(KOREN, "data", "raw")
API = "https://cs.wikipedia.org/w/api.php"
UA = "conBond2/0.1 (vyzkum aktivacniho pole; jindrich.nemec@yahoo.com)"
PAUZA = 1.0

# Čeští spisovatelé napříč obdobími. Vybráno tak, aby přibylo, co v korpusu
# chybí — obrození, poezie, meziválečná próza, exil i současnost —, ne aby
# to bylo dvanáctkrát totéž.
AUTORI = [
    "Alois Jirásek", "Karel Havlíček Borovský", "Karel Jaromír Erben",
    "Jaroslav Vrchlický", "Julius Zeyer", "Svatopluk Čech", "Petr Bezruč",
    "Vítězslav Hálek", "Jiří Wolker", "František Halas", "Vladimír Holan",
    "František Hrubín", "Karel Poláček", "Eduard Bass", "Marie Majerová",
    "Ota Pavel", "Josef Škvorecký", "Arnošt Lustig", "Ivan Klíma",
    "Ludvík Vaculík", "Václav Havel", "Egon Hostovský",
]


def klic(jmeno: str) -> str:
    """Jméno článku → jméno souboru. Týž tvar jako u dosavadních dvanácti:
    malými písmeny, mezery podtržítky — z něj se pak dělá identita entity."""
    return jmeno.lower().replace(" ", "_")


def stahnout(jmeno: str):
    """Čistý text článku. `explaintext` vrátí to, co je vidět, bez značek."""
    url = API + "?" + urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": "1",
        "redirects": "1", "format": "json", "titles": jmeno,
    })
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    stranky = data.get("query", {}).get("pages", {})
    for _, s in stranky.items():
        if "extract" in s and s["extract"].strip():
            return s["extract"]
    return None


def main() -> int:
    nastavit(uroven="info")
    os.makedirs(SUROVE, exist_ok=True)
    znovu = "--znovu" in sys.argv
    mam = {j[:-4] for j in os.listdir(SUROVE) if j.endswith(".txt")}

    chybi = [a for a in AUTORI if znovu or klic(a) not in mam]
    print(f"v data/raw je {len(mam)} článků · seznam má {len(AUTORI)}"
          f" · stáhne se {len(chybi)}")
    if "--seznam" in sys.argv:
        for a in chybi:
            print(f"  {a}  →  {klic(a)}.txt")
        return 0

    stazeno = znaku = 0
    for a in chybi:
        time.sleep(PAUZA)
        text = stahnout(a)
        if not text:
            log.info("článek nenalezen", kdo=a)
            continue
        cesta = os.path.join(SUROVE, klic(a) + ".txt")
        with open(cesta, "w", encoding="utf-8") as f:
            f.write(text)
        stazeno += 1
        znaku += len(text)
        log.info("uloženo", kdo=klic(a), znaku=len(text))
    print(f"\nstaženo {stazeno} článků, {znaku} znaků")
    print("dál:  python3 scripts/baseline.py vse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
