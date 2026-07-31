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
from collections import Counter, defaultdict

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Pole, UlozisteSouboru, nastavit_log  # noqa: E402
from core.tvrzeni import INSTANCE, PODTRIDA, Tvrzeni, Znalost  # noqa: E402

ZLATA = os.path.join(KOREN, "data", "gold", "otazky.json")

# Tázací tvar → druh místa, kde odpověď leží. Tohle je celá „sémantika"
# otázky: zbytek udělá pole.
CO_HLEDAT = {"kdy": "Typ=cas", "kde": "Typ=misto", "kam": "Typ=misto",
             "odkud": "Typ=misto", "kolik": "Typ=pocet"}

# Tvary, které o obsahu nic neříkají — svítily by skoro všude a průnik by
# zbytečně zúžily na nic.
PRAZDNA = {"se", "si", "je", "byl", "byla", "bylo", "v", "na", "z", "do",
           "a", "i", "s", "o", "u", "k", "ve", "?", ".", ","}


def nacist_zlatou():
    with open(ZLATA, encoding="utf-8") as f:
        return json.load(f)


class Odpovidac:
    """Otázka dovnitř, aktivace a odpověď ven."""

    def __init__(self, pole: Pole, znalost: Znalost = None):
        self.pole = pole
        self.znalost = znalost or Znalost()
        self.slovnik = pole.ziskat_slovnik()
        self.vety = pole.uloziste.nacist_korpus("facts")
        self.podle_typu = self._sestavit_navesky()
        self.podle_entity = self._sestavit_entity()

    def _sestavit_entity(self):
        """Entita → věty, ve kterých o ní je řeč. Klíč je z Ent=, protože
        jméno v té větě obvykle nestojí."""
        out = defaultdict(set)
        for vi, veta in enumerate(self.vety):
            for t in veta:
                for a in t["acts"]:
                    if a.startswith("Ent="):
                        out[a[4:]].add(vi)
        return out

    def najit_entitu(self, tvary) -> str:
        """Jméno z otázky → klíč entity. Stačí, když sedí příjmení."""
        kusy = {t.lower() for t in tvary}
        nejlepsi, skore = "", 0
        for klic in self.podle_entity:
            casti = set(klic.split("_"))
            shoda = len(casti & kusy)
            if shoda > skore:
                nejlepsi, skore = klic, shoda
        return nejlepsi

    def _sestavit_navesky(self):
        """Věta → typ → rozsahy, které agenti označili."""
        out = defaultdict(lambda: defaultdict(list))
        for vi, veta in enumerate(self.vety):
            for t in veta:
                for n in t.get("navesky", ()):
                    out[vi][n["typ"]].append(tuple(n["rozsah"]))
        return out

    # ---- aktivace ----------------------------------------------------
    def obsahove_tvary(self, text: str) -> list:
        kusy = text.replace("?", " ").replace(".", " ").split()
        return [k.lower() for k in kusy
                if k.lower() not in PRAZDNA and k.lower() not in CO_HLEDAT]

    def vety_tvaru(self, tvar: str) -> set:
        """Ve kterých větách faktů tvar svítí. Tohle je ta aktivace."""
        p = self.slovnik.najit(tvar)
        return set(p.vety["f"]) if p else set()

    def rozsvitit(self, text: str) -> dict:
        """Co se z otázky aktivuje.

        Dva různé kanály, protože osoba a děj se v poli chovají jinak:
        sloveso je TVAR a najde se ve slovníku, osoba je AKTIVACE `Ent=`
        a ve větě jako slovo většinou vůbec není."""
        tvary = self.obsahove_tvary(text)
        entita = self.najit_entitu(tvary)
        vety_entity = set(self.podle_entity.get(entita, ()))
        # slovesa a zbytek: co z toho svítí ve slovníku
        zbytek = [t for t in tvary if t not in set(entita.split("_"))]
        kde = {t: self.vety_tvaru(t) for t in zbytek}
        zname = {t: v for t, v in kde.items() if v}
        podle_tvaru = set.intersection(*zname.values()) if zname else set()
        if vety_entity and podle_tvaru:
            prunik = vety_entity & podle_tvaru
        else:
            prunik = vety_entity or podle_tvaru
        return {
            "tvary": tvary,
            "entita": entita,
            "vet_entity": len(vety_entity),
            "svitici": {t: len(v) for t, v in kde.items()},
            "nezname": [t for t, v in kde.items() if not v],
            "vety": prunik,
            "sablony": self.sablony_vet(prunik),
        }

    def sablony_vet(self, vety: set) -> set:
        """Které faktové šablony v tom poli leží."""
        f = self.pole.fakta
        out = set()
        for i, radek in enumerate(f.tok.radky):
            if not radek.je_prazdny and radek.veta in vety and i in f.slovo_radku:
                out.add(f.slovo_radku[i][1])
        return out

    # ---- expanze znalostí --------------------------------------------
    def rozsirit(self, tvar: str) -> set:
        """Věty, které tvar zasáhne PŘES ZNALOST. Otázka na spisovatele
        míří i na Hrabala; opačně to neplatí.

        Potomek se hledá napřed jako ENTITA a teprve pak jako tvar — jinak
        by expanze našla jen věty, kde jméno doopravdy stojí, což je u
        pro-dropu zlomek."""
        vety = set()
        for potomek in self.znalost.potomci(tvar.lower()):
            klic = self.najit_entitu(potomek.split())
            if klic:
                vety |= self.podle_entity[klic]
            else:
                for kus in potomek.split():
                    vety |= self.vety_tvaru(kus)
        return vety

    # ---- odpověď -----------------------------------------------------
    def urcit_typ(self, text: str):
        for slovo in text.lower().replace("?", " ").split():
            if slovo in CO_HLEDAT:
                return CO_HLEDAT[slovo]
        return None

    def odpovedet(self, text: str, se_znalosti: bool = False) -> dict:
        akt = self.rozsvitit(text)
        vety = set(akt["vety"])
        pomohla = set()
        if se_znalosti:
            for t in akt["tvary"]:
                sirsi = self.rozsirit(t)
                if sirsi:
                    pomohla |= sirsi
            if pomohla:
                vety = (vety | pomohla) if not vety else (vety & pomohla) or vety
        typ = self.urcit_typ(text)
        nalezy = []
        for vi in sorted(vety):
            for rozsah in self.podle_typu.get(vi, {}).get(typ, ()):
                nalezy.append((vi, rozsah, self.text_rozsahu(vi, rozsah)))
        return {"aktivace": akt, "typ": typ, "vety": vety, "nalezy": nalezy,
                "znalost_pomohla": bool(pomohla),
                "odpoved": nalezy[0][2] if nalezy else None}

    def text_rozsahu(self, vi: int, rozsah) -> str:
        veta = self.vety[vi]
        return " ".join(veta[j]["form"] for j in rozsah if j < len(veta))

    def text_vety(self, vi: int) -> str:
        return " ".join(t["form"] for t in self.vety[vi]) \
            .replace(" .", ".").replace(" ,", ",")


def zmerit(o: Odpovidac, zlata, se_znalosti=False):
    v_poli = presne = bez_kandidatu = 0
    kandidatu = []
    podle_typu = Counter()
    for z in zlata:
        v = o.odpovedet(z["text"], se_znalosti)
        if not v["nalezy"]:
            bez_kandidatu += 1
            continue
        kandidatu.append(len(v["nalezy"]))
        spravne = (z["veta"], tuple(z["rozsah"]))
        mista = [(vi, r) for vi, r, _ in v["nalezy"]]
        if spravne in mista:
            v_poli += 1
            podle_typu[z["typ"]] += 1
            if mista[0] == spravne:
                presne += 1
    n = len(zlata)
    return {"n": n, "v_poli": v_poli, "presne": presne,
            "bez_kandidatu": bez_kandidatu,
            "prumer_kandidatu": sum(kandidatu) / len(kandidatu) if kandidatu else 0,
            "podle_typu": podle_typu}


def vypsat_mereni(jmeno, m):
    n = m["n"]
    print(f"  {jmeno:<22} zásah pole {m['v_poli']:>3}/{n} ({100*m['v_poli']/n:>4.0f} %)"
          f" · přesně {m['presne']:>3}/{n} ({100*m['presne']/n:>4.0f} %)"
          f" · bez kandidátů {m['bez_kandidatu']:>3}"
          f" · průměr {m['prumer_kandidatu']:.1f} kandidátů")


def ukazat(o: Odpovidac, zlata, kolik: int):
    for z in zlata[:kolik]:
        v = o.odpovedet(z["text"])
        a = v["aktivace"]
        print(f"\n  ── {z['text']}")
        svit = ", ".join(f"{t} ({n} vět)" for t, n in a["svitici"].items() if n)
        print(f"     osoba:     Ent={a['entita'] or '—'} → {a['vet_entity']} vět")
        print(f"     tvary:     {svit or 'nic'}")
        if a["nezname"]:
            print(f"     nesvítí:   {', '.join(a['nezname'])}")
        print(f"     průnik:    {len(a['vety'])} vět · {len(a['sablony'])} šablon"
              f" · hledám {v['typ']}")
        if not v["nalezy"]:
            print("     odpověď:   — v poli není nic toho typu")
        else:
            for vi, r, txt in v["nalezy"][:3]:
                znak = "✓" if (vi, tuple(r)) == (z["veta"], tuple(z["rozsah"])) else " "
                print(f"     {znak} {txt!r}  (věta {vi})")
            if len(v["nalezy"]) > 3:
                print(f"       …a dalších {len(v['nalezy']) - 3}")
        print(f"     zlatá:     {z['odpoved']!r}")


def ukazat_znalost(o: Odpovidac):
    """Vztahy zadané průběžně mění, co otázka zasáhne."""
    print("\n  Znalost se zadává větou a čte se AŽ PŘI POROVNÁNÍ — v datech")
    print("  se nic nemění, jen se otázka smí zobecnit.\n")
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
        print(f"     bez znalosti: {len(bez['vety'])} vět, "
              f"{len(bez['nalezy'])} kandidátů → {bez['odpoved']!r}")
        print(f"     se znalostí:  {len(se['vety'])} vět, "
              f"{len(se['nalezy'])} kandidátů → {se['odpoved']!r}")
        if se["nalezy"]:
            print("     první tři: " + " · ".join(
                repr(t) for _, _, t in se["nalezy"][:3]))


def main():
    nastavit_log(uroven="ticho")
    pole = Pole(UlozisteSouboru(config=Config.nacist()))
    pole.nastavit_polomery(1, 1)
    pole.postavit()
    zlata = nacist_zlatou()
    o = Odpovidac(pole)
    f = pole.fakta
    print(f"korpus: {len(o.vety)} vět · {f.pocet_stredu()} slov"
          f" · {f.pocet_sablon()} šablon · slovník {len(o.slovnik)} tvarů")
    print(f"zlatá sada: {len(zlata)} otázek "
          f"({', '.join(f'{k} {v}' for k, v in Counter(z['typ'] for z in zlata).items())})\n")

    if "--ukaz" in sys.argv:
        i = sys.argv.index("--ukaz")
        kolik = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 6
        ukazat(o, zlata, kolik)
        return 0
    if "--znalost" in sys.argv:
        ukazat_znalost(o)
        return 0

    vypsat_mereni("obsahové tvary", zmerit(o, zlata))
    zasahy = zmerit(o, zlata)["podle_typu"]
    celkem = Counter(z["typ"] for z in zlata)
    print("\n  po typech otázky:")
    for typ, n in celkem.items():
        print(f"    {typ:<12} {zasahy.get(typ, 0):>3}/{n:<4} "
              f"({100*zasahy.get(typ, 0)/n:>4.0f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
