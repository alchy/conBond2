#!/usr/bin/env python3
"""CommonsenseQA — měření, jestli má smysl to stavět. Ne stavba.

    python3 scripts/csqa.py [kolik]

PROČ NEJDŘÍV MĚŘENÍ. Dedukce, kterou dataset vyžaduje

    Fox ⇒ WildAnimal ⇒ LivesIn(NaturalHabitat)

v datech NENÍ. CommonsenseQA dává otázku, pět možností a klíč; premisy musí
přijít odjinud. Kdybych je napsal, měřil bych vlastní znalost světa, ne
odvozování — a ve dvanácti tisících otázkách by to bylo mnohem hůř vidět
než v jednom `if`.

Poctivý vnější zdroj je ConceptNet, protože **CommonsenseQA z něj vznikla**:
otázky byly generované z jeho trojic. Bere se tedy tam, kde je zamýšlený.

CO SE MĚŘÍ, A PROČ NE PŘESNOST. Pět možností znamená 20 % náhodou, takže
jedno číslo nic neřekne — a hlavně trestá to, co je na tomhle systému
cenné: že mlčí, když neví. Měří se proto trojice, stejně jako u pole:

    dosah        u kolika otázek vůbec vznikne opora
    přesnost     z těch s oporou kolik trefí klíč
    vyloučení    kolik možností jde odepsat — a JAK ČASTO se tím
                 odepíše ta správná

Poslední číslo je to nejdůležitější a jediné, které může celý nápad
zabít. Rozměr smí vylučovat jen tehdy, když vylučuje bezpečně; kdyby
odepisoval správné odpovědi, je horší než náhoda.

OPORA SE POČÍTÁ NASLEPO. Klíč se použije až při vyhodnocení, nikdy při
rozhodování — jinak by se měřilo, jak dobře umím číst odpověď.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(KOREN, "data", "lexicon", "conceptnet_cache.json")

CSQA = ("https://datasets-server.huggingface.co/rows?dataset=tau%2Fcommonsense_qa"
        "&config=default&split=validation&offset={od}&length={n}")
CN = ("https://datasets-server.huggingface.co/filter?"
      "dataset=peandrew%2Fconceptnet_en_nomalized&config=default&split=train"
      "&where={kde}&limit=100")

# Vztahy, které nesou umístění nebo zařazení. `atlocation` a `isa` jsou
# přesně ty dvě, které úloha o lišce potřebuje; ostatní (antonym, synonym)
# by opora nebyla.
NOSNE = ("atlocation", "isa", "partof", "usedfor", "capableof", "hasproperty",
         "hascontext", "relatedto", "hasa", "madeof", "receivesaction",
         "locatednear", "definedas")


def stahni(url: str, pokusu: int = 5):
    for i in range(pokusu):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:            # noqa: BLE001 — síť selže jakkoli
            if i == pokusu - 1:
                print(f"    (nedostupné: {e})", file=sys.stderr)
                return None
            time.sleep(3 * (i + 1))
    return None


class Sit:
    """ConceptNet přes filtrovací dotaz, s pamětí na disku.

    Nestahuje se celý dump (2,6 milionu hran): potřebujeme okolí pár set
    pojmů a stažení celku by si vyžádalo knihovnu navíc. Projekt drží
    backend na standardní knihovně a kvůli jednomu měření se to porušovat
    nemá."""

    def __init__(self, cesta: str = CACHE):
        self.cesta = cesta
        self.pamet: dict = {}
        self.selhalo: set = set()
        if os.path.exists(cesta):
            with open(cesta, encoding="utf-8") as f:
                self.pamet = json.load(f)

    def ulozit(self):
        os.makedirs(os.path.dirname(self.cesta), exist_ok=True)
        with open(self.cesta, "w", encoding="utf-8") as f:
            json.dump(self.pamet, f, ensure_ascii=False)

    def okoli(self, pojem: str) -> list:
        """Hrany, kde pojem stojí vlevo. Vrací [(rel, druhý konec)]."""
        klic = pojem.lower().replace(" ", "_")
        if klic in self.pamet:
            return self.pamet[klic]
        kde = urllib.parse.quote(f'"arg1"=\'{klic}\'')
        d = stahni(CN.format(kde=kde))
        if d is None:
            # SELHÁNÍ SE NEUKLÁDÁ. První verze si prázdný výsledek zapsala
            # do paměti a od té chvíle vypadal výpadek sítě jako pojem bez
            # hran: `people` má 1821 hran a měření mu dalo nula, čímž si
            # nafouklo právě ta čísla, která měla rozhodovat.
            #
            # Nula je nejnebezpečnější hodnota, protože „data to nemají"
            # a „nepodařilo se zeptat" vypadají stejně.
            self.selhalo.add(klic)
            return []
        hrany = [[r["row"]["rel"], r["row"]["arg2"]] for r in d.get("rows", [])]
        self.pamet[klic] = hrany
        return hrany


def opora(sit: Sit, pojem: str, moznost: str) -> dict:
    """Kolik a jaká opora vede od pojmu otázky k té možnosti.

    Dva kroky, ne víc. Na jeden skok („fox --atlocation--> forest") se
    trefí zlomek otázek; na tři už vede cesta odkudkoli kamkoli a přestává
    to něco znamenat — táž věc, jakou dnes ukázala Praha v grafu osob.

    DRUHÝ KROK SE POČÍTÁ PRŮNIKEM, NE PROCHÁZENÍM. První verze volala okolí
    pro každého souseda zvlášť; `fox` jich má 262, takže na jednu otázku
    vyšlo přes tisíc dotazů a měření by běželo hodiny. Sousedství obou
    konců stačí stáhnout jednou a protnout — šest dotazů na otázku.
    """
    cil = moznost.lower().replace(" ", "_")
    hrany = sit.okoli(pojem)
    for rel, druhy in hrany:
        if druhy == cil and rel in NOSNE:
            return {"kroku": 1, "druh": "trida" if rel in ("isa", "definedas")
                    else "primo", "pres": [rel]}
    # PŘES ZAŘAZENÍ, NEBO PŘÍMO? Tohle je ten rozdíl, který úloha zkouší:
    #
    #   fox --isa--> wild_animal --atlocation--> natural_habitat   typické
    #   fox --atlocation--> hen_house                              možné
    #
    # Obojí je „dosažitelné" a první měření je nerozlišilo. Cesta přes
    # třídu tvrdí, kam to PATŘÍ; přímá hrana jen, kde se to může vyskytnout.
    tridy = {d: r for r, d in hrany if r in ("isa", "definedas")}
    tam = {d: r for r, d in sit.okoli(cil) if r in NOSNE}
    pres_tridu = sorted(set(tridy) & set(tam))
    if pres_tridu:
        u = pres_tridu[0]
        return {"kroku": 2, "druh": "trida", "pres": [tridy[u], tam[u]], "uzel": u}
    odtud = {d: r for r, d in hrany if r in NOSNE}
    spolecne = sorted(set(odtud) & set(tam))
    if spolecne:
        u = spolecne[0]
        return {"kroku": 2, "druh": "asociace", "pres": [odtud[u], tam[u]],
                "uzel": u}
    return {"kroku": 0}


def main() -> int:
    kolik = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    d = stahni(CSQA.format(od=0, n=min(kolik, 100)))
    if not d:
        print("CommonsenseQA nedostupná")
        return 1
    otazky = [r["row"] for r in d["rows"]][:kolik]
    sit = Sit()

    s_oporou = trefa = preskoceno = 0
    podle = {d: {"otazek": 0, "trefa": 0, "kandidatu": 0}
             for d in ("trida", "primo", "asociace")}
    vyloucenych = zabitych = 0
    celkem_moznosti = 0
    print(f"  {len(otazky)} otázek · ConceptNet přes filtrovací dotaz\n")
    for i, o in enumerate(otazky):
        pojem = o["question_concept"]
        texty = o["choices"]["text"]
        labely = o["choices"]["label"]
        pred = len(sit.selhalo)
        opory = [opora(sit, pojem, t) for t in texty]
        if len(sit.selhalo) > pred:
            # Otázka, u které se něco nepodařilo stáhnout, do měření nejde.
            # Počítat ji jako „bez opory" by chybu sítě vydávalo za nález.
            preskoceno += 1
            continue
        celkem_moznosti += len(texty)
        bez = [j for j, x in enumerate(opory) if x["kroku"] == 0]
        vyloucenych += len(bez)
        # Klíč se použije AŽ TEĎ — rozhodovalo se naslepo.
        spravny = labely.index(o["answerKey"])
        if spravny in bez:
            zabitych += 1
        for d in ("trida", "primo", "asociace"):
            kdo = [j for j, x in enumerate(opory) if x.get("druh") == d]
            if kdo:
                podle[d]["otazek"] += 1
                podle[d]["trefa"] += (spravny in kdo)
                podle[d]["kandidatu"] += len(kdo)
        nej = min(range(len(opory)),
                  key=lambda j: (opory[j]["kroku"] or 9))
        if opory[nej]["kroku"]:
            s_oporou += 1
            trefa += (nej == spravny)
        if i < 6:
            znak = "✓" if opory[spravny]["kroku"] else "✗"
            print(f"  {znak} {pojem} → {o['question'][:52]}")
            for j, t in enumerate(texty):
                z = "«klíč»" if j == spravny else "      "
                k = opory[j]
                cesta = (f"{k['kroku']} krok  {'→'.join(k['pres'])}"
                         + (f" přes {k['uzel']}" if k.get("uzel") else "")
                         if k["kroku"] else "bez opory")
                print(f"       {z} {t:<22} {cesta}")
        if i % 10 == 9:
            sit.ulozit()
    sit.ulozit()

    merenych = len(otazky) - preskoceno
    print(f"\n  {'měřeno':<26} {merenych}/{len(otazky)}"
          f"   (vyřazeno {preskoceno} kvůli výpadku sítě)")
    print(f"  {'dosah':<26} {s_oporou}/{merenych}"
          f"  ({100*s_oporou/max(merenych,1):.0f} %)")
    if s_oporou:
        print(f"  {'přesnost z opřených':<26} {trefa}/{s_oporou}"
              f"  ({100*trefa/s_oporou:.0f} %)   náhoda 20 %")
    print(f"  {'možností bez opory':<26} {vyloucenych}/{celkem_moznosti}"
          f"  ({100*vyloucenych/celkem_moznosti:.0f} %)")
    print(f"  {'z toho zabito správných':<26} {zabitych}/{max(merenych,1)}"
          f"  ({100*zabitych/max(merenych,1):.0f} %)   ← tohle rozhoduje")
    print(f"\n  PODLE DRUHU OPORY — rozlišuje zařazení tam, kde asociace ne?")
    print(f"  {'druh':<12} {'otázek':>7} {'klíč mezi nimi':>15} {'prům. kandidátů':>17}")
    for d, x in podle.items():
        if not x["otazek"]:
            continue
        print(f"  {d:<12} {x['otazek']:>7} {x['trefa']:>10} "
              f"({100*x['trefa']/x['otazek']:>3.0f} %) {x['kandidatu']/x['otazek']:>16.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
