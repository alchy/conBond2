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

    Bere se výhradně DEFINIČNÍ VĚTA, tedy ta s nejmenším `vd` v dokumentu,
    ve které narození stojí.

    První verze brala nejmenší rok narození a největší rok úmrtí z celého
    článku. Znělo to odolně a bylo to vedle: Nerudovi tak vyšlo
    `(1784, 1891)`, protože 1784 je rok narození jeho OTCE ze třetí věty.
    Krajní hodnota přes celý dokument nesbírá překlepy, sbírá cizí lidi.
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
            vd = t.get("vd")
            if vd is None:
                continue
            zaznam = out.setdefault(dok, {"n": None, "z": None,
                                          "vd_n": None, "vd_z": None})
            klic, klic_vd = ("n", "vd_n") if udal == "Udal=narozeni" else ("z", "vd_z")
            if zaznam[klic_vd] is None or vd < zaznam[klic_vd]:
                zaznam[klic], zaznam[klic_vd] = r, vd
    return {d: (v["n"], v["z"]) for d, v in out.items()}


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
