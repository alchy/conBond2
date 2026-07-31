#!/usr/bin/env python3
"""Přenášejí se šablony mezi tématy?

    python3 scripts/domeny.py

PROČ TO MĚŘIT. Korpus byl dlouho jen životopisy spisovatelů, takže šablony
mohly být tvarem životopisu, ne tvarem češtiny. Teprve druhé téma to
rozhodne: když se vzory postavené na životopisech objeví i u fotosyntézy
a u psa domácího, je to obecné místo ve větě; když ne, naučili jsme se
jenom jeden žánr.

Je to zkouška thése o PODHOUBÍ: jestli se tematický základ postaví jednou
a každý další text jím projde, musí být přenos vidět jako číslo.

CO SE POČÍTÁ

    sdílené vzory   kolik šablon žije ve VÍC doménách naráz
    přenos          kolik procent slov nové domény padne do vzoru,
                    který už znala doména stará
    vlastní         vzory, které má doména jen sama pro sebe

Domény se poznají z `dok` — původ věty, který se drží mimo `acts`.
"""

import os
import sys
from collections import Counter, defaultdict

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Pole, UlozisteSouboru, nastavit_log  # noqa: E402

# Jak se z dokumentu pozná doména. Životopis má v článku osobu, ostatní ne —
# a protože to jde poznat z dat (Ent= na kořeni), nemusí se to psát ručně.
ZVIRATA = ("pes_domácí", "kočka_domácí", "kůň_domácí", "koza_domácí",
           "ovce_domácí", "prase_domácí", "králík_domácí", "skot")

# Biblické knihy poznáme podle jména souboru. Je to jiný druh textu než
# Wikipedie — přímá řeč, archaická čeština, žádný encyklopedický rám —
# a proto je to zátěžová zkouška přenosu, ne další porce téhož.
BIBLE = "bible_"


def domena(dok: str, zivotopisy: set) -> str:
    if dok.startswith(BIBLE):
        return "bible"
    if dok in ZVIRATA:
        return "zvířata"
    return "životopisy" if dok in zivotopisy else "věci a jevy"


def main() -> int:
    nastavit_log(uroven="ticho")
    pole = Pole(UlozisteSouboru(config=Config.nacist()))
    pole.nastavit_polomery(1, 1)
    pole.postavit()
    f = pole.fakta

    # Životopis = článek, kde koreference našla osobu. Bere se z dat.
    zivotopisy = set()
    for radek in f.tok.radky:
        if radek.je_prazdny:
            continue
        for a in radek.token["acts"]:
            if a.startswith("Ent="):
                zivotopisy.add(radek.token.get("dok"))
    zivotopisy -= set(ZVIRATA)
    zivotopisy = {d for d in zivotopisy if not (d or "").startswith(BIBLE)}

    # řádek → doména, šablona → domény
    dom_radku, sablona_domen = {}, defaultdict(set)
    slov = Counter()
    for i, radek in enumerate(f.tok.radky):
        if radek.je_prazdny or i not in f.slovo_radku:
            continue
        d = domena(radek.token.get("dok", ""), zivotopisy)
        dom_radku[i] = d
        slov[d] += 1
        sablona_domen[f.slovo_radku[i][1]].add(d)

    domeny = sorted(slov)
    print(f"korpus: {f.pocet_stredu()} slov · {f.pocet_sablon()} šablon"
          f" · {len(zivotopisy)} životopisů\n")
    print(f"  {'doména':<16} {'slov':>8} {'vzorů':>8} {'jen svých':>10} {'sdílených':>10}")
    print("  " + "─" * 58)
    for d in domeny:
        vzory = {s for s, ds in sablona_domen.items() if d in ds}
        jen = {s for s in vzory if sablona_domen[s] == {d}}
        print(f"  {d:<16} {slov[d]:>8} {len(vzory):>8} {len(jen):>10}"
              f" {len(vzory) - len(jen):>10}")

    # PŘENOS: kolik slov domény padne do vzoru, který zná i jiná doména
    print(f"\n  přenos — podíl slov, jejichž vzor zná i jiná doména:")
    for d in domeny:
        pokryto = sum(1 for i, x in dom_radku.items()
                      if x == d and len(sablona_domen[f.slovo_radku[i][1]]) > 1)
        print(f"    {d:<16} {pokryto:>7}/{slov[d]:<7} {100*pokryto/slov[d]:>5.1f} %")

    # A ta nejpodstatnější otázka: co z toho je jen prázdné okolí?
    print(f"\n  vzory ve VŠECH {len(domeny)} doménách naráz: "
          f"{sum(1 for ds in sablona_domen.values() if len(ds) == len(domeny))}")
    nejsirsi = sorted((s for s, ds in sablona_domen.items() if len(ds) == len(domeny)),
                      key=lambda s: -len(f.vypsat_sablony()[s]["tvary"]))[:5]
    for s in nejsirsi:
        info = f.vypsat_sablony()[s]
        print(f"    {s:<9} {len(info['tvary']):>4} tvarů · "
              f"{' '.join(info['vec'][:5])}")
        print(f"              {', '.join(sorted(info['tvary'])[:8])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
