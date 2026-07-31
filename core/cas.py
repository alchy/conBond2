"""Čas jako kódovaný rozměr — první implementace švu `Rozmer`.

ODKUD. „Mohla Božena Němcová znát Emanuela Halmana?" se dřív rozhodovalo
dvěma `if`y v `graph.py`, které jsem napsal ručně, protože vím, jak funguje
čas. Systém o tom nevěděl nic a nemohl to ověřit.

Tenhle modul dělá dvě oddělené věci a ta hranice je celý smysl:

    KÓDUJE      z korpusu přečte životy a dvojici OZNAČÍ
                `disjunktni` / `prekryv` / `neznamo`
    NEROZHODUJE co ta značka znamená, určí až měření nad doloženými
                dvojicemi (`dimensions.zmerit`)

Kdyby modul rovnou tvrdil „disjunktní ⇒ nemožné", byl by to týž zapečený
axiom, jen schovaný o patro níž.

ROK, NE DATUM. Bio dodává `Udal=narozeni` a `Udal=umrti` s typem `Typ=cas`;
z hodnoty se bere jen ROK. Na otázku „mohli se potkat" je den zbytečně
přesný a přesnost, kterou data neunesou, plodí falešné zápory.

`Udal=zivot` SE NEBERE. Je to letopočet ze závorky nebo z průběhu života —
studia, svatba, vydání knihy. Vzít ho jako narození znamená posunout
člověku život; tenhle projekt na to jednou doplatil, když se Bio přiřkl
data manželky a roky studií.
"""

import re
from typing import Iterable, Mapping, Optional

from .dimensions import DISJUNKTNI, NEZNAMO, PREKRYV, Rozmer

ROK = re.compile(r"\b(1[0-9]{3}|20[0-2][0-9])\b")


def rok(text: str) -> Optional[int]:
    m = ROK.search(text or "")
    return int(m.group(1)) if m else None


def zivoty_z_korpusu(vety: Iterable) -> dict:
    """Dokument → (narození, úmrtí) v letech; chybějící údaj je None.

    Bere se NEJMENŠÍ rok u narození a NEJVĚTŠÍ u úmrtí. Životopis zmiňuje
    víc dat a rozbor se občas splete; krajní hodnota je proti překlepu
    odolnější než první nalezená a hlavně je určená — první nalezená
    závisí na pořadí vět.
    """
    out: dict = {}
    for veta in vety:
        for t in veta:
            udal = next((a for a in t["acts"] if a.startswith("Udal=")), "")
            if udal not in ("Udal=narozeni", "Udal=umrti"):
                continue
            if "Typ=cas" not in t["acts"]:
                continue
            r = rok(t["form"])
            dok = (t.get("dok") or "").replace("_", " ")
            if not r or not dok:
                continue
            n, z = out.get(dok, (None, None))
            if udal == "Udal=narozeni":
                n = r if n is None else min(n, r)
            else:
                z = r if z is None else max(z, r)
            out[dok] = (n, z)
    return out


class Cas(Rozmer):
    """Překrývaly se ty dva životy?"""

    jmeno = "cas"

    def __init__(self, zivoty: Mapping):
        self.zivoty = dict(zivoty)

    def hodnota(self, entita: str):
        return self.zivoty.get((entita or "").lower())

    def vztah(self, a, b) -> str:
        """Značka, ne závěr.

        `disjunktni` znamená jen tolik, že jeden interval skončil dřív, než
        druhý začal. Zda z toho něco plyne, rozhodne měření.

        Chybějící krajní datum dává `neznamo`, ne `prekryv`. Kdo ještě
        neumřel — nebo se jen neví kdy — nemá být prohlášen za současníka
        každého; monotónní pole platí i tady."""
        (na, za), (nb, zb) = a, b
        if za is not None and nb is not None and za < nb:
            return DISJUNKTNI
        if zb is not None and na is not None and zb < na:
            return DISJUNKTNI
        if na is not None and nb is not None and za is not None and zb is not None:
            return PREKRYV
        return NEZNAMO
