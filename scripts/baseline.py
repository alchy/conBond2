#!/usr/bin/env python3
"""Baseline korpus: články o spisovatelích → data/corpora/facts.json.

Náš původní korpus měl 86 tokenů faktů. Na měření zobecnění je to o dva až
tři řády málo — jakýkoli poměr z něj spočítaný je šum. Tenhle má kolem
padesáti tisíc slov.

Průchod má tři kroky a každý se dá spustit zvlášť:

    python3 scripts/baseline.py vety      # text → věty (bez rozboru)
    python3 scripts/baseline.py rozbor    # věty → tokeny (lokální UDPipe)
    python3 scripts/baseline.py koreference   # doplní podměty
    python3 scripts/baseline.py zapis     # agenti + druh výpovědi + korpus
    python3 scripts/baseline.py vse

DOPLŇOVÁNÍ PODMĚTU je tu schválně jako vlastní krok a jeho výsledek je
v poli VIDĚT. Životopisný článek mluví většinou o jedné osobě a věty jako
„Narodil se v Praze." podmět vůbec nemají (pro-drop) nebo mají jen „On".
Takový fakt pak nejde spojit s otázkou „Kde se narodil Hrabal?", protože
o Hrabalovi nic neříká.

Nepřidáváme kvůli tomu do textu slova, která tam nejsou — pole má zůstat
obrazem textu. Místo toho dostane sloveso dvě aktivace navíc:

    Kor=prodrop     podmět ve větě chybí
    Kor=zajmeno     podmět je zájmeno 3. osoby
    Ent=hrabal      a tohle je ten, o kom se mluví

Je to heuristika, ne rozřešení koreference: v životopise je hlavní osoba
článku tak převažující antecedent, že prostá shoda rodu a čísla stačí. Kolik
případů to zasáhne a kolik z nich shoda rodu potvrdí, skript vypíše — ať se
dá posoudit, čemu se dá věřit.
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config  # noqa: E402
from core.agents import oznacit_korpus  # noqa: E402
from core.ingest import Cistic, Rozbor  # noqa: E402
from core.log import log, nastavit  # noqa: E402

SUROVE = os.path.join(KOREN, "data", "raw")
MEZIKROK = os.path.join(KOREN, "data", "raw", "_vety.json")
ROZEBRANE = os.path.join(KOREN, "data", "raw", "_tokeny.json")
CIL = os.path.join(KOREN, "data", "corpora", "facts.json")

# Řádky, které do korpusu nepatří: nadpisy sekcí, odkazy, holé seznamy.
NEPATRI = re.compile(r"^\s*(==|\*|#|\|)|^\s*$")
# Věta kratší než tohle je skoro jistě zbytek po čištění, ne věta.
MIN_SLOV = 4


# ---- 1. text → věty ------------------------------------------------------
def krok_vety() -> dict:
    clanky = {}
    for jmeno in sorted(os.listdir(SUROVE)):
        if not jmeno.endswith(".txt"):
            continue
        klic = jmeno[:-4]
        clanky[klic] = Cistic().ze_souboru(os.path.join(SUROVE, jmeno))
        log.info("článek načten", kdo=klic, odstavcu=len(clanky[klic]))
    with open(MEZIKROK, "w", encoding="utf-8") as f:
        json.dump(clanky, f, ensure_ascii=False, indent=1)
    log.info("odstavce uloženy", clanku=len(clanky),
             odstavcu=sum(len(v) for v in clanky.values()))
    return clanky


# ---- 2. věty → tokeny ----------------------------------------------------
def krok_rozbor(config) -> dict:
    with open(MEZIKROK, encoding="utf-8") as f:
        clanky = json.load(f)
    rozbor = Rozbor(config.udpipe)
    out = {}
    for kdo, odstavce in clanky.items():
        zacatek = time.perf_counter()
        vety = []
        # Po dávkách, ať se nepošle celý článek v jednom požadavku.
        for i in range(0, len(odstavce), 25):
            vety.extend(rozbor.vety_slovniku("\n".join(odstavce[i:i + 25])))
        out[kdo] = vety
        log.info("rozebráno", kdo=kdo, vet=len(vety),
                 tokenu=sum(len(v) for v in vety),
                 s=round(time.perf_counter() - zacatek, 1))
    with open(ROZEBRANE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out


# ---- 3. doplnění podmětu -------------------------------------------------
def rod_cislo(token: dict) -> tuple:
    rod = cislo = None
    for a in token["acts"]:
        if a.startswith("Gender="):
            rod = set(a.split("=", 1)[1].split(","))
        elif a.startswith("Number="):
            cislo = a.split("=", 1)[1]
    return rod, cislo


def hlavni_osoba(kdo: str, vety: list) -> dict:
    """Kdo je hlavní osoba článku.

    Identita je JMÉNO ČLÁNKU, ne lemma z rozboru. První pokus bral z věty
    první PROPN v podmětu a dostal „bohumil", „božena", „karel" — tedy holá
    křestní jména. To je přesně díra, kterou popisuje předchozí projekt:
    fakt navěšený na „Karel" patřil všem sedmadvaceti Karlům v korpusu.
    Jméno souboru je jednoznačné a nic se nehádá.

    Z rozboru se bere jen rod a číslo, aby šlo ověřit shodu."""
    rod, cislo = {"Masc"}, "Sing"
    for veta in vety[:3]:
        for t in veta:
            if t["upos"] == "PROPN" and "nsubj" in t["acts"]:
                r, c = rod_cislo(t)
                return {"id": kdo, "rod": r or rod, "cislo": c or cislo}
    return {"id": kdo, "rod": rod, "cislo": cislo}


def je_koren_slovesa(t: dict) -> bool:
    return "root" in t["acts"] and t["upos"] in ("VERB", "AUX")


def podmet_korene(veta: list, koren: dict):
    """Podmět KOŘENE, ne libovolný podmět ve větě.

    První pokus hledal nsubj kdekoli — jenže věty na Wikipedii jsou dlouhé a
    skoro každá má někde vedlejší větu s vlastním podmětem, takže se pro-drop
    nenašel skoro nikdy (83 z 3478 vět). Rozhoduje závislost na kořeni."""
    for t in veta:
        if t.get("head") == koren.get("id") and (
                "nsubj" in t["acts"] or "nsubj:pass" in t["acts"]):
            return t
    return None


def je_treti_osoba(t: dict) -> bool:
    """Je kořen ve 3. osobě?

    Čeština v minulém čase osobu na slovese NENESE: „Narodil se" má
    Gender=Masc Number=Sing Tense=Past a žádné Person=. První pokus proto
    filtroval na Person=3 a zahodil 1188 z 1588 slovesných kořenů — tedy
    právě ty věty, o které v životopise jde.

    Bereme tedy: buď je Person=3 přímo, nebo osoba není vyjádřená vůbec
    (příčestí), což u věty bez podmětu 3. osobu implikuje — první a druhá
    by měly pomocné sloveso „jsem" / „jsi"."""
    if "Person=3" in t["acts"]:
        return True
    if any(a.startswith("Person=") for a in t["acts"]):
        return False                      # výslovně 1. nebo 2. osoba
    return "VerbForm=Part" in t["acts"] or "VerbForm=Fin" in t["acts"]


def je_zajmeno_3(t: dict) -> bool:
    return ("nsubj" in t["acts"] and "PronType=Prs" in t["acts"]
            and "Person=3" in t["acts"])


def je_to_ona(podmet: dict, osoba: dict) -> bool:
    """Je pojmenovaný podmět TA osoba, o které článek je?

    Měření ukázalo díru: 913 vět z 3478 (26 %) má vlastní pojmenovaný podmět
    — „Němcová", „Kundera", „Seifert" — a entitu nedostalo ŽÁDNOU, protože
    se doplňovala jen tam, kde podmět chybí. Otázka na tu osobu se pak k té
    větě nedostane, ačkoli ji jmenuje.

    Porovnává se lemma s kusy identity (jméno souboru), aby „Josef" u článku
    o Josefu Čapkovi sedlo a u článku o Karlovi ne."""
    if podmet["upos"] not in ("PROPN", "NOUN"):
        return False
    casti = set(osoba["id"].split("_"))
    lemma = podmet.get("lemma", podmet["form"]).lower()
    return lemma in casti or podmet["form"].lower() in casti


def je_proza(veta: list) -> bool:
    """Je to výpověď, nebo položka seznamu?

    Měření: 57 % „vět" v korpusu nemá slovesný kořen a při pohledu do nich
    je to bibliografie a soupisy děl — „Praha : Academia , 1985 .",
    „Wiener slawistischer Almanach , sv . 19 , 1987 , str . 101 – 122 .".
    Vysvětluje to i vzory, které v poli nesedaly: šablona plná cizích slov
    (als, arts, avantgarde, bei) je vzor CIZOJAZYČNÉ BIBLIOGRAFIE, ne češtiny.

    NEMAŽE SE TO. Pole má být obraz textu a v článku ta bibliografie je;
    zahodit půlku korpusu by navíc změnilo všechna dosud naměřená čísla.
    Místo toho se to OZNAČÍ a kdo měří výpovědi, si odfiltruje. Pro pole je
    to navíc užitečná osa: soused v bibliografii je jiné místo než soused ve
    větě, a bez příznaku to obojí padá do jedné šablony."""
    return any(je_koren_slovesa(t) for t in veta)


def oznacit_druh(vety: list) -> dict:
    """Každý token dostane, do jaké výpovědi patří. Na KAŽDÝ token schválně:
    šablona se skládá ze SOUSEDŮ, takže kdyby to nesl jen kořen, sousedi by
    o tom nevěděli a vzory by se nerozdělily."""
    pocty = {"proza": 0, "seznam": 0}
    for v in vety:
        druh = "proza" if je_proza(v) else "seznam"
        pocty[druh] += 1
        for t in v:
            if f"Vyp={druh}" not in t["acts"]:
                t["acts"].append(f"Vyp={druh}")
    return pocty


def krok_koreference() -> dict:
    with open(ROZEBRANE, encoding="utf-8") as f:
        clanky = json.load(f)
    souhrn = {"prodrop": 0, "zajmeno": 0, "jmenovana": 0,
              "shoda": 0, "neshoda": 0, "vet": 0}
    for kdo, vety in clanky.items():
        osoba = hlavni_osoba(kdo, vety)
        if not osoba:
            log.info("hlavní osoba nenalezena, přeskakuji", kdo=kdo)
            continue
        zasah = 0
        for veta in vety:
            souhrn["vet"] += 1
            koren = next((t for t in veta if je_koren_slovesa(t)), None)
            if koren is None or not je_treti_osoba(koren):
                continue
            podmet = podmet_korene(veta, koren)
            if podmet is None:
                druh = "prodrop"
            elif ("PronType=Prs" in podmet["acts"] and "Person=3" in podmet["acts"]):
                druh = "zajmeno"
            elif je_to_ona(podmet, osoba):
                # Podmět je vyjádřený a je to ona. Shodu neověřujeme —
                # jméno je jistější vodítko než rod slovesa.
                souhrn["jmenovana"] += 1
                souhrn["shoda"] += 1
                zasah += 1
                for a in ("Kor=jmenovana", f"Ent={osoba['id']}"):
                    if a not in koren["acts"]:
                        koren["acts"].append(a)
                continue
            else:
                continue
            # Shoda rodu a čísla. U minulého času je rod na slovese, jinak ne;
            # když ho sloveso nenese, shodu neověřujeme a jen to započítáme.
            rod, cislo = rod_cislo(koren)
            if rod is not None and not (rod & osoba["rod"]):
                souhrn["neshoda"] += 1
                continue
            if cislo is not None and cislo != osoba["cislo"]:
                souhrn["neshoda"] += 1
                continue
            souhrn["shoda"] += 1
            souhrn[druh] += 1
            zasah += 1
            for a in (f"Kor={druh}", f"Ent={osoba['id']}"):
                if a not in koren["acts"]:
                    koren["acts"].append(a)
        log.info("podměty doplněny", kdo=kdo, osoba=osoba["id"], zasahu=zasah,
                 podil=f"{100*zasah/max(len(vety),1):.0f} %")
    with open(ROZEBRANE, "w", encoding="utf-8") as f:
        json.dump(clanky, f, ensure_ascii=False)
    log.info("koreference hotova", **souhrn)
    return clanky


# ---- 4. zápis korpusu ----------------------------------------------------
def krok_zapis() -> None:
    with open(ROZEBRANE, encoding="utf-8") as f:
        clanky = json.load(f)
    # PŮVOD VĚTY. Bez něj se dá na větu odkazovat jen pozicí v korpusu — a ta
    # přežije přesně do příští přestavby. Doplatila na to zlatá sada: po
    # rozšíření z 12 na 34 článků ukazovala jinam a spadla ze 100 % na 0 %,
    # aniž by to cokoli ohlásilo.
    #
    # Drží se MIMO `acts`, stejně jako `hodnota`: do vektoru nesmí. Kdyby se
    # dostal dovnitř, rozpadly by se šablony po autorech — 34 hodnot na
    # každém tokenu je nejhorší možná kombinace pokrytí a mohutnosti.
    vety = []
    for kdo in sorted(clanky):
        for poradi, v in enumerate(clanky[kdo]):
            for t in v:
                t["dok"] = kdo
                t["vd"] = poradi          # pořadí věty v dokumentu
            vety.append(v)
    # Lemma do pole nepatří. `id` a `head` ANO — nejsou v `acts`, takže se
    # do vektoru nedostanou, ale bez nich nejde poznat, co na čem závisí.
    # První pokus je zahazoval a doplatily na to dvě věci: koreference brala
    # podmět odkudkoli z věty a generátor otázek věšel na kořen nález, který
    # patřil úplně jiné klauzuli („Kolik se narodil Mácha? → 16").
    for v in vety:
        for t in v:
            t.pop("lemma", None)
    # AGENTI JSOU KROK PŘÍPRAVY, ne něco, co se pustí zvlášť. Dřív se
    # spouštěli ad hoc a přepsáním korpusu mlčky zmizeli — přesně ta tichá
    # vada, na kterou conBond nasadil health.py.
    souhrn = oznacit_korpus(vety)
    log.info("agenti označili", **souhrn)
    pocty = oznacit_druh(vety)
    log.info("druh výpovědi označen", **pocty,
             podil_prozy=f"{100*pocty['proza']/max(len(vety),1):.0f} %")
    os.makedirs(os.path.dirname(CIL), exist_ok=True)
    with open(CIL, "w", encoding="utf-8") as f:
        json.dump(vety, f, ensure_ascii=False)
    log.info("korpus zapsán", vet=len(vety),
             tokenu=sum(len(v) for v in vety),
             kB=round(os.path.getsize(CIL) / 1024))
    doplnit_vertikaly(vety)


def doplnit_vertikaly(vety: list) -> None:
    """Nové aktivace musí dostat svůj sloupec, jinak by v poli nebyly vidět."""
    cesta = os.path.join(KOREN, "data", "verticals", "verticals.json")
    vychozi = os.path.join(KOREN, "data", "defaults", "verticals.json")
    with open(cesta if os.path.exists(cesta) else vychozi, encoding="utf-8") as f:
        cols = json.load(f)
    zname = {c["a"] for c in cols}
    nove = {}
    for v in vety:
        for t in v:
            for a in t["acts"]:
                if a in zname or a in nove:
                    continue
                if a.startswith(("Kor=", "Ent=")):
                    nove[a] = "KOR"
                elif a.startswith("Vyp="):
                    nove[a] = "VÝP"
                else:
                    nove[a] = skupina_aktivace(a)
    for a, g in sorted(nove.items(), key=lambda x: (x[1], x[0])):
        cols.append({"a": a, "g": g})
    os.makedirs(os.path.dirname(cesta), exist_ok=True)
    with open(cesta, "w", encoding="utf-8") as f:
        json.dump(cols, f, ensure_ascii=False, indent=1)
    log.info("vertikály doplněny", novych=len(nove), celkem=len(cols))
    for g in sorted({g for g in nove.values()}):
        kolik = sum(1 for x in nove.values() if x == g)
        log.info("  nová skupina", skupina=g, sloupcu=kolik)


def skupina_aktivace(a: str) -> str:
    if "=" not in a:
        return "UPOS" if a.isupper() else "DEPREL"
    return "FEATS"


# ---- běh -----------------------------------------------------------------
def main() -> int:
    config = Config.nacist()
    nastavit(uroven="info", soubor=os.path.join(config.slozka_behu(), "baseline.log"))
    prikaz = sys.argv[1] if len(sys.argv) > 1 else "vse"
    with log.krok(f"baseline {prikaz}"):
        if prikaz in ("vety", "vse"):
            krok_vety()
        if prikaz in ("rozbor", "vse"):
            krok_rozbor(config)
        if prikaz in ("koreference", "vse"):
            krok_koreference()
        if prikaz in ("zapis", "vse"):
            krok_zapis()
    return 0


if __name__ == "__main__":
    sys.exit(main())
