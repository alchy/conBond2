#!/usr/bin/env python3
"""Odpovědi na otázky ze spisovatelského korpusu — a hlavně: CO SE AKTIVUJE.

    python3 scripts/odpovedi.py            # měření na celé zlaté sadě
    python3 scripts/odpovedi.py --ukaz 8   # osm otázek rozepsaných
    python3 scripts/odpovedi.py --znalost  # co přidá průběžně zadaná znalost

JAK SE ODPOVÍDÁ. Ne vyhledáváním v textu. Otázka se rozloží na tvary, každý
tvar se najde ve SPOLEČNÉM slovníku a ten řekne, ve kterých větách faktů
svítí. Průnik těch množin je pole kandidátů; tázací tvar (Kdy / Kde) řekne,
jaký DRUH místa v něm hledat, a agenti Chronos a Topos ta místa označili
předem. Odpověď je to, co v průniku svítí správným typem.

JMÉNO SE PODLE TVARU NAJÍT NEDÁ. Ve 169 ze 170 zlatých vět jméno z otázky
VŮBEC NENÍ: čeština podmět zahazuje („Narodil se na brněnském předměstí
Židenice…") a identita sedí jako atribut `Ent=bohumil_hrabal`, který doplnila
koreference při stavbě korpusu. Hledat podle tvaru dalo 1 %. Osoba se proto
hledá jako AKTIVACE, ne jako slovo — a je to týž mechanismus, jakým se pak
navěsí cokoli dalšího, co o ní řekne dialog.

DVA STUPNĚ, PROTOŽE JINAK SE TRESTÁ ZÁMĚR.

    pole odpovědi   je odpověď mezi tím, co se aktivovalo?
                    tohle dělá aktivační pole
    zúžení          vybere se z toho ta jedna správná?
                    tohle pole nedělá — je to úloha pro identitu

Šablona neidentifikuje jednu odpověď, ale DRUH místa, kde odpověď leží.
„Kde se narodil X?" má trefit rodiště u všech autorů naráz.

CO S TÍM DĚLÁ ZNALOST. Vztahy zadané dialogem se čtou až při porovnání, ne
v datech. Otázka smí zobecňovat: kdo se ptá na spisovatele, míří i na
Hrabala, protože `hrabal ∈ spisovatel`. Fakt zobecňovat nesmí — proto se
expanduje jenom tady.
"""

import json
import os
import sys
from collections import Counter

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Odpovidac, Pole, UlozisteSouboru, nastavit_log  # noqa: E402
from core.tvrzeni import INSTANCE, PODTRIDA, Tvrzeni, Znalost  # noqa: E402

ZLATA = os.path.join(KOREN, "data", "gold", "otazky.json")


def nacist_zlatou(o=None):
    """Zlatá sada s klíčem DOKUMENT + pořadí věty v něm, ne pozicí v korpusu.

    Pozice přežije jen do příští přestavby: po rozšíření z 12 na 34 článků
    ukazovala jinam a měření spadlo ze 100 % na 0 %, aniž by to cokoli
    ohlásilo. Kdo tu sadu čte, musí ten klíč přeložit — a tady je to jedno
    místo, aby se překlad nemohl tiše rozejít."""
    with open(ZLATA, encoding="utf-8") as f:
        zlata = json.load(f)
    if o is None:
        return zlata
    kam = {}
    for vi, veta in enumerate(o.vety):
        if veta:
            kam[(veta[0].get("dok"), veta[0].get("vd"))] = vi
    ven, ztraceno = [], 0
    for z in zlata:
        vi = kam.get((z.get("dok"), z.get("vd")))
        if vi is None:
            ztraceno += 1
            continue
        ven.append(dict(z, veta=vi))
    if ztraceno:
        print(f"  pozor: {ztraceno} otázek se v korpusu nenašlo podle klíče")
    return ven


def zmerit(o: Odpovidac, zlata, se_znalosti=False):
    v_poli = presne = bez = 0
    kandidatu = []
    podle_typu = Counter()
    for z in zlata:
        v = o.odpovedet(z["text"], se_znalosti)
        if not v["kandidati"]:
            bez += 1
            continue
        kandidatu.append(len(v["kandidati"]))
        spravne = (z["veta"], tuple(z["rozsah"]))
        mista = [(k["veta"], tuple(k["rozsah"])) for k in v["kandidati"]]
        if spravne in mista:
            v_poli += 1
            podle_typu[z["typ"]] += 1
            if mista[0] == spravne:
                presne += 1
    return {"n": len(zlata), "v_poli": v_poli, "presne": presne, "bez": bez,
            "prumer": sum(kandidatu) / len(kandidatu) if kandidatu else 0,
            "podle_typu": podle_typu}


def ukazat(o: Odpovidac, zlata, kolik: int):
    for z in zlata[:kolik]:
        v = o.odpovedet(z["text"])
        a = v["aktivace"]
        svit = ", ".join(f"{t} ({n})" for t, n in a["svitici"].items() if n)
        print(f"\n  ── {z['text']}")
        print(f"     osoba:  Ent={a['entita'] or '—'} → {a['vet_entity']} vět")
        print(f"     tvary:  {svit or 'nic'}"
              + (f"   nesvítí: {', '.join(a['nezname'])}" if a["nezname"] else ""))
        print(f"     pole:   {v['vet']} vět · hledám {v['typ']}"
              + ("  (sloveso nesedlo, beru celou osobu)" if a.get("siroko") else ""))
        for k in v["kandidati"][:3]:
            znak = "✓" if (k["veta"], tuple(k["rozsah"])) == (z["veta"], tuple(z["rozsah"])) else " "
            print(f"     {znak} {k['text']!r}  (věta {k['veta']})")
        if len(v["kandidati"]) > 3:
            print(f"       …a dalších {len(v['kandidati']) - 3}")
        if not v["kandidati"]:
            print("     — v poli není nic toho druhu")
        print(f"     zlatá:  {z['odpoved']!r}")


def ukazat_znalost(o: Odpovidac):
    print("\n  Znalost se čte AŽ PŘI POROVNÁNÍ — v datech se nemění nic.\n")
    for t in (Tvrzeni(INSTANCE, "hrabal", "spisovatel"),
              Tvrzeni(INSTANCE, "čapek", "spisovatel"),
              Tvrzeni(INSTANCE, "seifert", "spisovatel"),
              Tvrzeni(PODTRIDA, "spisovatel", "člověk")):
        o.znalost.prijmi(t)
        print(f"    přijato: {t}")
    for otazka in ("Kde se narodil spisovatel?", "Kdy se narodil člověk?"):
        bez = o.odpovedet(otazka, se_znalosti=False)
        se = o.odpovedet(otazka, se_znalosti=True)
        print(f"\n  ── {otazka}")
        print(f"     bez znalosti: {bez['vet']} vět, {len(bez['kandidati'])} kandidátů")
        print(f"     se znalostí:  {se['vet']} vět, {len(se['kandidati'])} kandidátů"
              + ("  → " + " · ".join(repr(k["text"]) for k in se["kandidati"][:3])
                 if se["kandidati"] else ""))


def main():
    nastavit_log(uroven="ticho")
    pole = Pole(UlozisteSouboru(config=Config.nacist()))
    pole.nastavit_polomery(1, 1)
    pole.postavit()
    o = Odpovidac(pole)
    zlata = nacist_zlatou(o)
    f = pole.fakta
    print(f"korpus: {len(o.vety)} vět · {f.pocet_stredu()} slov"
          f" · {f.pocet_sablon()} šablon · slovník {len(o.slovnik)} tvarů")
    s_ent = sum(1 for v in o.vety if any(a.startswith("Ent=") for t in v for a in t["acts"]))
    print(f"vět s entitou: {s_ent}/{len(o.vety)} ({100*s_ent/len(o.vety):.0f} %)"
          "  ← zlatá sada je právě tenhle podíl")
    print(f"zlatá sada: {len(zlata)} otázek\n")

    if "--ukaz" in sys.argv:
        i = sys.argv.index("--ukaz")
        ukazat(o, zlata, int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 6)
        return 0
    if "--znalost" in sys.argv:
        ukazat_znalost(o)
        return 0

    m = zmerit(o, zlata)
    n = m["n"]
    print(f"  zásah pole {m['v_poli']:>3}/{n} ({100*m['v_poli']/n:>4.0f} %)"
          f" · přesně {m['presne']:>3}/{n} ({100*m['presne']/n:>4.0f} %)"
          f" · bez kandidátů {m['bez']:>3} · průměr {m['prumer']:.1f}")
    celkem = Counter(z["typ"] for z in zlata)
    print("\n  po typech otázky:")
    for typ, k in celkem.items():
        print(f"    {typ:<12} {m['podle_typu'].get(typ, 0):>3}/{k:<4} "
              f"({100*m['podle_typu'].get(typ, 0)/k:>4.0f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
