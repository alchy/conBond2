"""Krok 5 workflow: složit otázku ze slovníku, bez věty.

Otázku nemusíš napsat a nechat rozebrat; můžeš ji poskládat z tvarů, které
ve slovníku už jsou. Vznikne tím týž druh objektu — uspořádaná posloupnost
slov, ze které se složí vektor stejného tvaru jako z rozebrané věty.

POŘADÍ JE VÝZNAMNÉ, protože šablona není množina, ale vektor s offsety.
KOTVOU JE TÁZACÍ TVAR: offsety se počítají od něj, protože právě on určuje,
na co se ptáme. UD ho nerozliší — jak, kdy, kam, kde a proč mají jeden a týž
podpis, takže bez vlastní vertikály Ptá= by pět různých otázek spadlo do
jedné šablony.
"""

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from .window import Okno, zapsat_offset
from .interfaces import SkladacVektoru, ZdrojAktivaci
from .lexicon import Slovnik
from .sources import PRAZDNO


@dataclass
class Vzor:
    """Rozdělaná otázka. `kotva` je index tázacího tvaru, -1 = zatím žádný."""
    slova: list = field(default_factory=list)
    kotva: int = -1
    cile: list = field(default_factory=list)

    def je_hotovy(self) -> bool:
        return bool(self.slova) and self.kotva >= 0 and bool(self.cile)

    def tazaci_tvar(self) -> Optional[str]:
        return self.slova[self.kotva] if self.kotva >= 0 else None

    def do_slovniku(self) -> dict:
        return {"typ": self.tazaci_tvar(), "q": list(self.slova),
                "kotva": self.kotva, "f": list(self.cile)}

    @classmethod
    def ze_slovniku(cls, d: Mapping) -> "Vzor":
        return cls(slova=list(d.get("q", [])),
                   kotva=int(d.get("kotva", -1)),
                   cile=list(d.get("f", [])))


class Skladac:
    """Sestavuje vzor a umí z něj složit vektor."""

    def __init__(self, slovnik: Slovnik, zdroj: ZdrojAktivaci,
                 skladac: SkladacVektoru, okno: Okno):
        self.slovnik = slovnik
        self.zdroj = zdroj
        self.skladac = skladac
        self.okno = okno
        self.vzor = Vzor()

    # ---- sestavování -------------------------------------------------
    def zvolit_kotvu(self, tvar: str) -> "Skladac":
        self.vzor.slova.append(tvar)
        self.vzor.kotva = len(self.vzor.slova) - 1
        return self

    def pridat_slovo(self, tvar: str) -> "Skladac":
        self.vzor.slova.append(tvar)
        return self

    def odebrat_slovo(self, i: int) -> "Skladac":
        """Odebrání slova PŘED kotvou kotvu posune; odebrání kotvy ji zruší,
        nepřeskočí na cizí slovo."""
        self.vzor.slova.pop(i)
        if i == self.vzor.kotva:
            self.vzor.kotva = -1
        elif i < self.vzor.kotva:
            self.vzor.kotva -= 1
        return self

    def prepnout_cil(self, tvar: str) -> "Skladac":
        if tvar in self.vzor.cile:
            self.vzor.cile.remove(tvar)
        else:
            self.vzor.cile.append(tvar)
        return self

    def vycistit(self) -> "Skladac":
        self.vzor = Vzor()
        return self

    # ---- odvození ----------------------------------------------------
    def spocitat_offsety(self) -> list[tuple[str, int]]:
        if self.vzor.kotva < 0:
            return [(t, 0) for t in self.vzor.slova]
        return [(t, i - self.vzor.kotva) for i, t in enumerate(self.vzor.slova)]

    def slozit_vektor(self) -> dict:
        """Vektor složené otázky i s tím, co je na něm nejisté."""
        casti, mimo_okno, nezname, nejiste = [], [], [], []
        for tvar, d in self.spocitat_offsety():
            # Kotva sama do vektoru nepatří, když je střed nastavený mimo —
            # není to „za oknem", je to záměr. Hlásit ji jako mimo okno by
            # svádělo k tomu zvětšovat r, což by nepomohlo.
            if d == 0 and not self.okno.stred_uvnitr:
                continue
            if not self.okno.zasahuje(d):
                mimo_okno.append(tvar)
                continue
            aktivace = self.vypsat_aktivace_tvaru(tvar)
            if aktivace is None:
                nezname.append(tvar)
                casti.append(self.skladac.popsat_slot(d, []))
                continue
            if self.spocitat_jistotu(tvar) > 1:
                nejiste.append(tvar)
            casti.append(self.skladac.popsat_slot(d, aktivace))
        return {
            "vektor": self.skladac.slozit_vektor(casti),
            "mimo_okno": mimo_okno, "nezname": nezname, "nejiste": nejiste,
        }

    def vypsat_aktivace_tvaru(self, tvar: str) -> Optional[list[str]]:
        """Naklikané slovo si aktivace přinese ze slovníku. Kde má tvar víc
        sad, bere se nejčastější — a hlásí se to, místo tichého hádání."""
        polozka = self.slovnik.najit(tvar)
        if polozka is None:
            return None
        sada = polozka.vypsat_nejcastejsi_sadu()
        if sada is None:
            return None
        return self.zdroj.seradit_kanonicky(self.zdroj.odfiltrovat_typy(sada))

    def spocitat_jistotu(self, tvar: str) -> int:
        polozka = self.slovnik.najit(tvar)
        return polozka.spocitat_jistotu() if polozka else 0

    def najit_shodnou_sablonu(self, vektor, sablony: Mapping[str, dict]) -> Optional[str]:
        klic = self.skladac.spocitat_klic(vektor)
        for oznaceni, info in sablony.items():
            if self.skladac.spocitat_klic(info["vec"]) == klic:
                return oznaceni
        return None

    def popsat_vzor(self) -> str:
        if self.vzor.kotva < 0:
            return ", ".join(self.vzor.slova)
        return " ".join(f"{zapsat_offset(d)}:{t}" for t, d in self.spocitat_offsety())


def popsat_zaznam(zaznam: Mapping) -> dict:
    """Popis uložené dvojice. Starší záznamy kotvu nemají — jsou to množiny."""
    kotva = zaznam.get("kotva", -1)
    if not isinstance(kotva, int) or kotva < 0:
        return {"typ": None, "text": ", ".join(zaznam.get("q", []))}
    slova = zaznam.get("q", [])
    return {
        "typ": zaznam.get("typ") or (slova[kotva] if kotva < len(slova) else None),
        "text": " ".join(f"{zapsat_offset(i - kotva)}:{t}" for i, t in enumerate(slova)),
    }
