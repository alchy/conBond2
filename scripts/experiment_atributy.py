#!/usr/bin/env python3
"""Kolik sdílení stojí každá vrstva atributů?

Otázka „máme přidat atributy?" je měřitelná: stačí pole postavit několikrát
s různě velkou sadou a podívat se, co to udělá se sdílením. Křivka pak řekne,
co by udělalo přidání dalších.

Filtruje se přes šev ZdrojAktivaci — jádro se nemění, jen se mu podstrčí jiný
zdroj. Přesně na tohle ten šev je.

    python3 scripts/experiment_atributy.py
"""

import os
import sys

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Pole, UlozisteSouboru, nastavit_log  # noqa: E402
from core.sources import ZdrojZTokenu  # noqa: E402

# Rysy, o kterých revize tvrdí, že v poli nic nenesou.
PODEZRELE = ("NameType=", "Style=", "Hyph=", "Foreign=", "Abbr=",
             "Variant=", "NumForm=", "ConjType=", "AdpType=", "PrepCase=")
# Shodové rysy: u češtiny všudypřítomné, rozlišují i tam, kde nechceme.
SHODA = ("Gender=", "Number=", "Case=", "Animacy=", "Person=", "Gender[psor]=",
         "Number[psor]=")


class ZdrojSFiltrem(ZdrojZTokenu):
    """Zdroj aktivací, který navíc zahazuje, co se mu řekne."""

    def __init__(self, vertikaly, zahodit=(), **kw):
        super().__init__(vertikaly, **kw)
        self.zahodit = tuple(zahodit)

    def odfiltrovat_typy(self, acts):
        acts = super().odfiltrovat_typy(acts)
        if not self.zahodit:
            return acts
        return [a for a in acts if not a.startswith(self.zahodit)]


def zmerit(uloziste, nazev, zahodit, r=1):
    zdroj = ZdrojSFiltrem(uloziste.nacist_vertikaly(), zahodit=zahodit)
    pole = Pole(uloziste, zdroj=zdroj)
    pole.nastavit_polomery(r, r)
    pole.postavit(vzdy=True)
    f = pole.fakta
    sablony = f.vypsat_sablony()
    sdilene = [i for i in sablony.values() if len(i["tvary"]) > 1]
    pokryto = sum(len(i["radky"]) for i in sdilene)
    # kolik aktivací zbylo na token
    vsech = sum(len(zdroj.vypsat_aktivace(x.token))
                for x in f.tok.radky if not x.je_prazdny)
    return {
        "nazev": nazev,
        "akt_na_token": vsech / max(f.pocet_stredu(), 1),
        "sablon": f.pocet_sablon(),
        "pomer": f.spocitat_pomer(),
        "sdilenych": len(sdilene),
        "pokryto": 100 * pokryto / max(f.pocet_stredu(), 1),
    }


def main():
    nastavit_log(uroven="ticho")
    u = UlozisteSouboru(config=Config.nacist())
    sady = [
        ("vše, jak to je teď", ()),
        ("bez podezřelých rysů", PODEZRELE),
        ("bez shodových rysů", SHODA),
        ("bez obojího", PODEZRELE + SHODA),
        ("jen UPOS + DEPREL + naše vrstvy",
         ("Case=", "Gender=", "Number=", "Person=", "Tense=", "Mood=", "Voice=",
          "Aspect=", "VerbForm=", "Degree=", "Polarity=", "PronType=", "Animacy=",
          "NumType=", "NameType=", "Style=", "Hyph=", "Foreign=", "Abbr=",
          "Variant=", "NumForm=", "ConjType=", "AdpType=", "PrepCase=", "ExtPos=",
          "Poss=", "Reflex=", "Gender[psor]=", "Number[psor]=")),
    ]
    print("Sdílení vzorů podle toho, kolik atributů token nese  (fakta, r=1)")
    print("52 150 slov, 3478 vět, 12 spisovatelů\n")
    print(f"{'sada':<34} {'akt/token':>9} {'šablon':>8} {'poměr':>7}"
          f" {'sdílených':>10} {'slov ve sdílených':>18}")
    print("─" * 92)
    for nazev, zahodit in sady:
        v = zmerit(u, nazev, zahodit)
        print(f"{v['nazev']:<34} {v['akt_na_token']:>9.1f} {v['sablon']:>8}"
              f" {v['pomer']:>7.3f} {v['sdilenych']:>10} {v['pokryto']:>17.0f} %")
    print()
    print("Poměr blíž k nule = víc slov sdílí jeden vzor = víc zobecnění.")
    print("Poslední sloupec říká, kolik procent slov vůbec padne do vzoru,")
    print("který sdílí aspoň s jedním jiným slovem.")


if __name__ == "__main__":
    main()
