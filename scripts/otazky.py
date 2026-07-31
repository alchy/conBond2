#!/usr/bin/env python3
"""Sada otázek ke spisovatelskému korpusu + zlatá sada odpovědí.

    python3 scripts/otazky.py generuj    # z nálezů agentů složí otázky
    python3 scripts/otazky.py rozbor     # rozebere je lokálním UDPipe
    python3 scripts/otazky.py vse

JAK VZNIKAJÍ. Agenti našli v textu časy, místa a počty a víme, ke kterému
predikátu patří a o kom se ve větě mluví (`Ent=` z koreference). Z toho se
složí otázka a **cíl je znám ze stavby**, ne z dohadu:

    fakt    „Narodil se 28. března 1914 v Židenicích."   (podmět chybí!)
    Ent=    bohumil_hrabal
    otázka  „Kdy se narodil Bohumil Hrabal?"
    cíl     rozsah tokenů „28 . března 1914"

SLABINA, kterou je nutné říct nahlas: otázky vznikají ze stejných struktur,
které pole používá. Neměří se tedy „umí stroj odpovědět", ale „najde stroj
to, co mu bylo řečeno, že tam je". Zlatá sada psaná ručně by byla poctivější;
tahle je levná a velká. Pro srovnávání variant (víc/míň atributů, jiné r) to
stačí, pro tvrzení o absolutní úspěšnosti ne.

Jedna věc na ní přesto poctivá je: otázka pojmenuje autora, kdežto fakt ho
skoro nikdy neobsahuje — je v něm jen přes doplněný podmět. Zásah tedy
prochází vrstvou koreference, ne shodou slov.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config  # noqa: E402
from core.log import log, nastavit  # noqa: E402

FAKTA = os.path.join(KOREN, "data", "corpora", "facts.json")
DOTAZY = os.path.join(KOREN, "data", "corpora", "query.json")
ZLATA = os.path.join(KOREN, "data", "gold", "otazky.json")
SUROVE = os.path.join(KOREN, "data", "gold", "_otazky_text.json")

# Tázací tvar podle toho, co agent našel.
#
# POČET tu SCHVÁLNĚ NENÍ. Metron najde veličinu, ale ne odpověď na „kolik
# čeho" — vycházely z toho otázky „Kolik se podaří Olbracht? → oběma" nebo
# „Kolik získal Mácha? → jednom". Aby to dávalo smysl, musel by se počet
# vázat na předmět slovesa, ne jen na sloveso; to je víc práce, než co dnes
# potřebujeme, a špatná zlatá sada je horší než menší.
TAZACI = {"Typ=cas": "Kdy", "Typ=misto": "Kde"}


def jmeno_autora(klic: str) -> str:
    return " ".join(k.capitalize() for k in klic.split("_"))


def koren_vety(veta):
    return next((t for t in veta if "root" in t["acts"]
                 and t["upos"] in ("VERB", "AUX")), None)


def zvratne(veta, koren):
    """Zvratné se/si patří ke slovesu a bez něj otázka nedává smysl."""
    for t in veta:
        if t["form"].lower() in ("se", "si") and "expl:pv" in t["acts"]:
            return t["form"].lower()
    return None


# Slovesa, která sama o sobě nic neznamenají: fázová a modální. Bez
# doplnění vzniká otázka „Kde začal Jaroslav Hašek?", což není otázka —
# chybí, co začal. Je to valenční problém a pořádně by ho řešil VALLEX;
# tady stačí buď doplnění vzít z věty, nebo otázku vůbec nedělat.
NEUPLNA = {"začít", "začal", "začala", "začali", "přestat", "přestal",
           "přestala", "stát", "stal", "stala", "stali", "moci", "mohl",
           "mohla", "muset", "musel", "musela", "chtít", "chtěl", "chtěla",
           "snažit", "snažil", "snažila", "podařit", "podařilo", "zůstat",
           "zůstal", "zůstala", "pokusit", "pokusil", "pokusila"}


def doplneni(veta, koren):
    """Infinitivní doplnění kořene („začal PSÁT"). UD ho věší jako xcomp."""
    podle_id = {t.get("id"): t for t in veta if t.get("id") is not None}
    for t in veta:
        if t.get("head") != koren.get("id"):
            continue
        if "xcomp" in t["acts"] and "VerbForm=Inf" in t["acts"]:
            return t["form"].lower()
    return None


def entita(koren) -> str:
    for a in koren["acts"]:
        if a.startswith("Ent="):
            return a.split("=", 1)[1]
    return ""


def visi_na(veta, i, koren, kroku=2):
    """Závisí token i na kořeni, nejvýš přes `kroku` kroků?

    Přes jeden krok kvůli předložkám a shodným přívlastkům: „v Praze" visí
    Praha na slovese přes obl, ale „v roce 1925" má rok pod „roce". Dva kroky
    to pokryjí a dál už se dostáváme do cizích klauzulí."""
    podle_id = {t.get("id"): t for t in veta if t.get("id") is not None}
    t = veta[i]
    for _ in range(kroku + 1):
        if t.get("id") == koren.get("id"):
            return True
        t = podle_id.get(t.get("head"))
        if t is None:
            return False
    return False


def naveska_typu(veta, typ, koren=None):
    """Nález daného typu ve větě.

    U počtu se berou jen ZÁKLADNÍ číslovky. Řadové („první", „40.") nejsou
    odpověď na „kolik" — první pokus z nich dělal otázky jako „Kolikrát se
    stal Hrabal? → 40", což je nesmysl: to číslo patří do jiné klauzule
    a není to počet."""
    for i, t in enumerate(veta):
        for n in t.get("navesky", []):
            if n["typ"] != typ:
                continue
            if typ == "Typ=pocet" and not any(
                    a == "NumType=Card" for a in t["acts"]):
                continue
            if koren is not None and not visi_na(veta, i, koren):
                continue          # nález patří jiné klauzuli, ne našemu slovesu
            return n
    return None


def krok_generuj():
    vety = json.load(open(FAKTA, encoding="utf-8"))
    otazky, zlata = [], []
    videno = set()
    for vi, veta in enumerate(vety):
        koren = koren_vety(veta)
        if koren is None:
            continue
        kdo = entita(koren)
        if not kdo:
            continue                      # bez známého podmětu nemá otázka koho
        for typ, taz in TAZACI.items():
            n = naveska_typu(veta, typ, koren)
            if n is None:
                continue
            zv = zvratne(veta, koren)
            # Sloveso malým písmenem: v otázce nestojí na začátku věty,
            # takže „Kde se Narodil…" je překlep, ne velké písmeno jména.
            sloveso = koren["form"]
            if sloveso[:1].isupper() and koren["upos"] != "PROPN":
                sloveso = sloveso[0].lower() + sloveso[1:]
            dopl = doplneni(veta, koren)
            if sloveso.lower() in NEUPLNA:
                if dopl is None:
                    continue          # neúplné sloveso bez doplnění → není otázka
                sloveso = f"{sloveso} {dopl}"
            text = f"{taz} {zv + ' ' if zv else ''}{sloveso} {jmeno_autora(kdo)}?"
            klic = (text, vi)
            if klic in videno:
                continue
            videno.add(klic)
            otazky.append(text)
            zlata.append({"otazka": len(otazky) - 1, "text": text,
                          "veta": vi, "rozsah": n["rozsah"], "typ": typ,
                          "entita": kdo,
                          "odpoved": " ".join(veta[j]["form"] for j in n["rozsah"])})
    os.makedirs(os.path.dirname(ZLATA), exist_ok=True)
    json.dump(otazky, open(SUROVE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(zlata, open(ZLATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    poctem = {}
    for z in zlata:
        poctem[z["typ"]] = poctem.get(z["typ"], 0) + 1
    log.info("otázky složeny", celkem=len(otazky), **poctem)
    return otazky


def rozebrat(text, url, timeout=600):
    telo = urllib.parse.urlencode({
        "tokenizer": "", "tagger": "", "parser": "", "data": text}).encode("utf-8")
    with urllib.request.urlopen(url.rstrip("/") + "/process", telo, timeout=timeout) as r:
        odpoved = json.loads(r.read().decode("utf-8"))
    vety, tokeny = [], []
    for radek in odpoved.get("result", "").splitlines():
        if not radek.strip():
            if tokeny:
                vety.append(tokeny); tokeny = []
            continue
        if radek.startswith("#"):
            continue
        c = radek.split("\t")
        if len(c) < 8 or "-" in c[0] or "." in c[0]:
            continue
        rysy = [] if c[5] == "_" else c[5].split("|")
        tokeny.append({"form": c[1], "upos": c[3], "acts": [c[3], c[7]] + rysy})
    if tokeny:
        vety.append(tokeny)
    return vety


def krok_rozbor(config):
    otazky = json.load(open(SUROVE, encoding="utf-8"))
    ven = []
    for i in range(0, len(otazky), 40):
        davka = otazky[i:i + 40]
        vysledek = rozebrat("\n".join(davka), config.udpipe)
        # Jedna otázka = jedna věta; kdyby se rozpadla, bereme první část,
        # ať zůstane pořadí 1:1 se zlatou sadou.
        if len(vysledek) != len(davka):
            log.info("rozbor rozdělil otázku", davka=i, cekano=len(davka),
                     dostal=len(vysledek))
        ven.extend(vysledek[:len(davka)])
        while len(ven) < i + len(davka):
            ven.append([])
    # tázací tvar jako vlastní vertikála — UDPipe kde/kdy/jak nerozliší
    for v in ven:
        for t in v:
            if any(a.startswith("PronType=Int") for a in t["acts"]):
                a = "Ptá=" + t["form"].lower()
                if a not in t["acts"]:
                    t["acts"].append(a)
    json.dump(ven, open(DOTAZY, "w", encoding="utf-8"), ensure_ascii=False)
    log.info("dotazy zapsány", otazek=len(ven),
             tokenu=sum(len(v) for v in ven))
    doplnit_vertikaly(ven)


def doplnit_vertikaly(vety):
    cesta = os.path.join(KOREN, "data", "verticals", "verticals.json")
    vychozi = os.path.join(KOREN, "data", "defaults", "verticals.json")
    cols = json.load(open(cesta if os.path.exists(cesta) else vychozi, encoding="utf-8"))
    zname = {c["a"] for c in cols}
    nove = 0
    for v in vety:
        for t in v:
            for a in t["acts"]:
                if a in zname:
                    continue
                zname.add(a)
                g = ("PTÁ" if a.startswith("Ptá=") else
                     "FEATS" if "=" in a else
                     "UPOS" if a.isupper() else "DEPREL")
                cols.append({"a": a, "g": g})
                nove += 1
    json.dump(cols, open(cesta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log.info("vertikály doplněny", novych=nove, celkem=len(cols))


def main():
    config = Config.nacist()
    nastavit(uroven="info", soubor=os.path.join(config.slozka_behu(), "otazky.log"))
    prikaz = sys.argv[1] if len(sys.argv) > 1 else "vse"
    with log.krok(f"otázky {prikaz}"):
        if prikaz in ("generuj", "vse"):
            krok_generuj()
        if prikaz in ("rozbor", "vse"):
            krok_rozbor(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
