"""Převod modelu na JSON. Patří do knihovny, ne do serveru — jiný program
může chtít týž výstup, aniž by kolem něj stavěl HTTP.

Co se posílá ven, je záměrně jen to, co si prohlížeč nespočítá sám. Mřížku
si vykreslí z korpusu, který má; od jádra potřebuje ROZVRŽENÍ řádků (kde
jsou prázdné sloty), přiřazení šablon, vazby a sdílený slovník.
"""

from typing import Mapping, Optional, Sequence

from .field import KORPUSY, Pole
from .lexicon import Slovnik
from .side import Strana


def radky_strany(strana: Strana) -> list:
    """Rozvržení pole: na řádek dvojice [věta, pořadí tokenu] a null místo
    pořadí tam, kde je prázdný slot z odsazení."""
    return [[r.veta, None if r.je_prazdny else r.poradi_ve_vete]
            for r in strana.tok.radky]


def sablony_strany(strana: Strana, plny_vektor: bool = True) -> dict:
    out = {}
    for oznaceni, info in strana.vypsat_sablony().items():
        out[oznaceni] = {
            "vec": list(info["vec"]) if plny_vektor else list(info["vec"][:3]),
            "delka": len(info["vec"]),
            "tvary": sorted(info["tvary"]),
            "radky": list(info["radky"]),
        }
    return out


def vazby_strany(strana: Strana) -> list:
    return [{"w": v.tvar_cislo, "t": v.sablona, "vyskyty": v.vyskyty}
            for v in strana.vazby]


def sloty_strany(strana: Strana) -> dict:
    """Offsety slotů na střed. Klíč je index řádku, hodnota [[j, d], …]."""
    return {str(i): [[sl.j, sl.d] for sl in sloty]
            for i, sloty in strana.sloty_radku.items()}


def slovnik_ven(slovnik: Slovnik) -> list:
    out = []
    for p in slovnik.polozky:
        out.append({
            "tvar": p.tvar,
            "prazdny": p.je_prazdny,
            "radky": {"f": p.radky["f"], "q": p.radky["q"]},
            "vety": {"f": sorted(p.vety["f"]), "q": sorted(p.vety["q"])},
            "sablony": {"f": sorted(p.sablony["f"]), "q": sorted(p.sablony["q"])},
            "jistota": p.spocitat_jistotu(),
        })
    return out


def korpusy_ven(pole: Pole) -> dict:
    """Věty tak, jak je vidí jádro — tedy i s hrubými vrstvami a už bez
    toho, co je vypnuté. Prohlížeč jinak vykreslí mřížku, která neodpovídá
    vektoru: sloupec by v katalogu byl a v tokenu ne.

    Čte se to jen přes šev `vypsat_aktivace`, aby export nesahal zdroji
    dovnitř — jiná implementace zdroje odvozuje jinak nebo vůbec."""
    return {jmeno: [[dict(t, acts=list(pole.zdroj.vypsat_aktivace(t)))
                     for t in veta]
                    for veta in pole.uloziste.nacist_korpus(jmeno)]
            for jmeno in KORPUSY.values()}


def cisla_strany(strana: Strana) -> dict:
    prazdnych, celkem = strana.spocitat_prazdne_sloty()
    return {
        "radku": strana.tok.pocet_radku(),
        "stredu": strana.pocet_stredu(),
        "sablon": strana.pocet_sablon(),
        "vazeb": len(strana.vazby),
        "pomer": round(strana.spocitat_pomer(), 4),
        "slotu": strana.okno.pocet_slotu(),
        "prazdnych_slotu": prazdnych,
        "slotu_celkem": celkem,
    }


def strana_ven(strana: Strana, plny_vektor: bool = True) -> dict:
    return {
        "radky": radky_strany(strana),
        "sablony": sablony_strany(strana, plny_vektor),
        "vazby": vazby_strany(strana),
        "sloty": sloty_strany(strana),
        "cisla": cisla_strany(strana),
    }


def pole_ven(pole: Pole, *, s_korpusy: bool = False,
             plny_vektor: bool = True) -> dict:
    """Celý model. `s_korpusy` přiloží i věty — prohlížeč je potřebuje jen
    při prvním načtení, pak si je drží."""
    pole.postavit()
    ven = {
        "nastaveni": pole.nastaveni.do_slovniku(),
        "klic_mapovani": pole.ziskat_klic_mapovani(),
        "slovnik": slovnik_ven(pole.ziskat_slovnik()),
        "f": strana_ven(pole.fakta, plny_vektor),
        "q": strana_ven(pole.dotazy, plny_vektor),
    }
    if s_korpusy:
        # Katalog i s hrubými vrstvami — prohlížeč musí vidět tytéž sloupce
        # jako jádro, jinak by mřížka neodpovídala vektoru.
        ven["vertikaly"] = list(pole.vypsat_vertikaly())
        ven["korpusy"] = korpusy_ven(pole)
    return ven
