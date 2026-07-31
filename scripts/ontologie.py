#!/usr/bin/env python3
"""Typový svaz z Wikidat — stáhne se JEDNOU a uloží, běh zůstane offline.

    python3 scripts/ontologie.py stahni     # jediné místo, kde jde ven ze stroje
    python3 scripts/ontologie.py ukaz

PROČ WIKIDATA A NE WORDNET. Český WordNet by byl lepší — synsety a
hyperonymie jsou jeho obor — ale distribuuje se za placenou licenci.
Wikidata mají vlastnost P279 („podtřída čeho"), české popisky a licenci CC0.
Taxonomii dělají mimochodem, takže je místy podivná, ale je zdarma a je
v ní to podstatné.

PROČ NE Z KORPUSU. Předchozí projekt to zkusil vytěžit z kopulových vět a
vyšlo z toho „adresa ⊂ známý", „apoštol ⊂ stavba", „román ⊂ marný, práce,
smysl". Ze čtyř set uzlů bylo použitelných pár. Padesát tisíc slov na typový
svaz nestačí a nikdy stačit nebude.

SVAZ, NE STROM. Uzel má víc rodičů: `román` je zároveň *literární dílo* i
*próza*. Jedna cesta nahoru to nepopíše — a právě proto to má smysl brát
odjinud, ne kreslit ručně.

K ČEMU TO BUDE. Expanze při porovnání, ne v datech. Fakt nese `Typ=roman`,
dotaz se ptá na `Typ=dilo` a potkají se, protože svaz říká, že román je
dílo. Kdyby se expandovalo do dat, vektor se prodlouží a sdílení podle
našeho měření KLESNE — proto to patří do slučovače.

Expanze je asymetrická: dotaz smí zobecňovat nahoru, fakt ne. Otázka na
dílo smí trefit román; otázka na román nesmí trefit báseň, i když obojí je
dílo.
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

CIL = os.path.join(KOREN, "data", "ontology", "typy.json")
ENDPOINT = "https://query.wikidata.org/sparql"
UA = "conBond2/0.1 (vyzkum aktivacniho pole; jindrich.nemec@yahoo.com)"

# Pojmy, které nás zajímají. Stahuje se OD NICH NAHORU.
#
# První pokus procházel svaz shora dolů od „díla" a vyčerpal strop devíti set
# uzlů na šířce prvního patra — `román` ani `povídka` se do něj nevešly.
# Prohledávat dolů je špatný tvar úlohy: my víme, které pojmy chceme, a cesta
# nahoru je krátká a ohraničená.
POJMY = [
    "román", "novela", "povídka", "báseň", "básnická sbírka", "sbírka povídek",
    "drama", "divadelní hra", "esej", "fejeton", "cestopis", "pohádka",
    "libreto", "scénář", "memoáry", "literární dílo", "beletrie",
    "socha", "obraz", "kresba", "ilustrace", "malba", "grafika",
    "výtvarné dílo", "umělecké dílo", "dílo",
]
MAX_UZLU = 900
PAUZA = 0.3


def dotaz_sparql(dotaz: str, pokusu: int = 3):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": dotaz, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for pokus in range(pokusu):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            if pokus == pokusu - 1:
                log.info("dotaz vzdán", chyba=type(e).__name__)
                return []
            time.sleep(3)
    return []


def najdi_qid(jmeno: str):
    """QID podle přesného českého popisku."""
    dotaz = f"""
    SELECT ?x WHERE {{
      ?x rdfs:label "{jmeno}"@cs .
      ?x wdt:P279|wdt:P31 ?cokoliv .
    }} LIMIT 1
    """
    v = dotaz_sparql(dotaz)
    return v[0]["x"]["value"].rsplit("/", 1)[-1] if v else None


def nadrazene(qid: str) -> list:
    """Přímí rodiče uzlu i s českými jmény. Uzel jich má víc — je to svaz."""
    dotaz = f"""
    SELECT ?x ?xLabel WHERE {{
      wd:{qid} wdt:P279 ?x .
      ?x rdfs:label ?xLabel . FILTER(LANG(?xLabel) = "cs")
    }} LIMIT 30
    """
    return [(b["x"]["value"].rsplit("/", 1)[-1], b["xLabel"]["value"])
            for b in dotaz_sparql(dotaz)]


def krok_stahni():
    uzly, hrany = {}, {}
    fronta, videno = [], set()
    for jmeno in POJMY:
        time.sleep(PAUZA)
        q = najdi_qid(jmeno)
        if not q:
            log.info("pojem ve Wikidatech nenalezen", pojem=jmeno)
            continue
        uzly[q] = jmeno
        fronta.append(q)
        videno.add(q)
        log.info("pojem nalezen", pojem=jmeno, qid=q)
    # a teď NAHORU
    while fronta and len(uzly) < MAX_UZLU:
        qid = fronta.pop(0)
        time.sleep(PAUZA)
        rodice = nadrazene(qid)
        for q, jmeno in rodice:
            uzly.setdefault(q, jmeno)
            hrany.setdefault(qid, [])
            if q not in hrany[qid]:
                hrany[qid].append(q)
            if q not in videno:
                videno.add(q)
                fronta.append(q)
    os.makedirs(os.path.dirname(CIL), exist_ok=True)
    json.dump({"uzly": uzly, "nadrazene": hrany, "pojmy": POJMY},
              open(CIL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log.info("svaz uložen", uzlu=len(uzly), hran=sum(len(v) for v in hrany.values()),
             s_vice_rodici=sum(1 for v in hrany.values() if len(v) > 1),
             kB=round(os.path.getsize(CIL) / 1024))


def predci(data, qid, videno=None) -> set:
    """Všichni nadřazení, tranzitivně. Tohle je ta expanze."""
    videno = videno if videno is not None else set()
    for rodic in data["nadrazene"].get(qid, []):
        if rodic in videno:
            continue
        videno.add(rodic)
        predci(data, rodic, videno)
    return videno


def krok_ukaz():
    data = json.load(open(CIL, encoding="utf-8"))
    uzly, hrany = data["uzly"], data["nadrazene"]
    print(f"uzlů {len(uzly)} · hran {sum(len(v) for v in hrany.values())}")
    print(f"s víc rodiči (svaz, ne strom): {sum(1 for v in hrany.values() if len(v) > 1)}\n")
    podle_jmena = {j.lower(): q for q, j in uzly.items()}
    for slovo in ("román", "báseň", "socha", "povídka", "drama", "obraz",
                  "esej", "novela"):
        q = podle_jmena.get(slovo)
        if not q:
            print(f"  {slovo:<10} ve svazu není")
            continue
        cesta = [uzly.get(p, p) for p in predci(data, q)]
        print(f"  {slovo:<10} ⊂ {', '.join(sorted(cesta)[:8])}")


def main():
    nastavit(uroven="info")
    prikaz = sys.argv[1] if len(sys.argv) > 1 else "ukaz"
    if prikaz == "stahni":
        krok_stahni()
    krok_ukaz()
    return 0


if __name__ == "__main__":
    sys.exit(main())
