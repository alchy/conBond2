"""Krok 3 workflow: sdílený slovník tvarů.

Slovník je SPOLEČNÝ oběma stranám a plní se z obou. Že je týž tvar ve faktu
i v dotazu, samo o sobě nic nespojuje — je to jen společný prostor tvarů.
Spojení dělá až mapování.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping, Optional

from .interfaces import ZdrojAktivaci
from .flow import Tok
from .sources import PRAZDNY_TVAR

STRANY = ("f", "q")


@dataclass
class Polozka:
    tvar: str
    je_prazdny: bool = False
    radky: dict = field(default_factory=lambda: {"f": [], "q": []})
    vety: dict = field(default_factory=lambda: {"f": set(), "q": set()})
    sablony: dict = field(default_factory=lambda: {"f": set(), "q": set()})
    # Sady aktivací se počítají kvůli SKLÁDÁNÍ otázky ze slovníku: naklikané
    # slovo si musí odněkud přinést aktivace.
    sady: Counter = field(default_factory=Counter)
    _podle_klice: dict = field(default_factory=dict)

    def pocet_vyskytu(self, strana: str) -> int:
        return len(self.radky[strana])

    def je_v_obou(self) -> bool:
        return bool(self.radky["f"]) and bool(self.radky["q"])

    def vypsat_nejcastejsi_sadu(self) -> Optional[list[str]]:
        if not self.sady:
            return None
        klic, _ = self.sady.most_common(1)[0]
        return list(self._podle_klice[klic])

    def spocitat_jistotu(self) -> int:
        """Kolik různých sad aktivací tvar má. Jedna = jistota."""
        return len(self.sady)


class Slovnik:
    def __init__(self, zdroj: ZdrojAktivaci):
        self.zdroj = zdroj
        self.polozky: list[Polozka] = []
        self.index: dict[str, int] = {}

    # ---- plnění ------------------------------------------------------
    def naplnit_z_toku(self, tok: Tok, strana: str) -> "Slovnik":
        for i, radek in enumerate(tok.radky):
            self.zapsat_radek(radek, i, strana)
        return self

    def zapsat_radek(self, radek, i: int, strana: str) -> Polozka:
        tvar = PRAZDNY_TVAR if radek.je_prazdny else self.zdroj.urcit_tvar(radek.token)
        polozka = self.zalozit_nebo_najit(tvar, radek.je_prazdny)
        polozka.radky[strana].append(i)
        polozka.vety[strana].add(radek.veta)
        if not radek.je_prazdny:
            self.zapsat_sadu(polozka, radek.token["acts"])
        return polozka

    def zalozit_nebo_najit(self, tvar: str, je_prazdny: bool = False) -> Polozka:
        if tvar not in self.index:
            self.index[tvar] = len(self.polozky)
            self.polozky.append(Polozka(tvar=tvar, je_prazdny=je_prazdny))
        return self.polozky[self.index[tvar]]

    @staticmethod
    def zapsat_sadu(polozka: Polozka, acts) -> None:
        klic = "|".join(sorted(acts))
        polozka.sady[klic] += 1
        polozka._podle_klice.setdefault(klic, list(acts))

    def zapsat_sablonu(self, tvar: str, strana: str, oznaceni: str) -> None:
        self.najit(tvar).sablony[strana].add(oznaceni)

    # ---- čtení -------------------------------------------------------
    def najit(self, tvar: str) -> Optional[Polozka]:
        i = self.index.get(tvar)
        return self.polozky[i] if i is not None else None

    def cislo(self, tvar: str) -> Optional[int]:
        return self.index.get(tvar)

    def vypsat_tvary_v_obou(self) -> list[Polozka]:
        return [p for p in self.polozky if not p.je_prazdny and p.je_v_obou()]

    def vypsat_nejiste(self) -> list[Polozka]:
        """Tvary s víc sadami aktivací — u skládání se u nich hádá."""
        return [p for p in self.polozky if not p.je_prazdny and p.spocitat_jistotu() > 1]

    def __len__(self) -> int:
        return len(self.polozky)
