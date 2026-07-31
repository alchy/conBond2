"""Výchozí implementace tří švů: zdroj aktivací, skládač vektoru, slučovač.

Kdo chce jiné chování, podstrčí vlastní třídu se stejným rozhraním — jádro
se nemění.
"""

from typing import Any, Hashable, Iterable, Mapping, Sequence

from .window import zapsat_offset
from .interfaces import SkladacVektoru, Slucovac, ZdrojAktivaci

PRAZDNO = "∅"
PRAZDNY_TVAR = "<empty>"


class ZdrojZTokenu(ZdrojAktivaci):
    """Aktivace jsou rovnou v tokenu, kanonické pořadí dávají sloupce pole."""

    def __init__(self, vertikaly: Sequence[Mapping], *, typy: bool = True,
                 syrove: bool = False):
        self.poradi = self.sestavit_poradi(vertikaly)
        self.typy = typy
        self.syrove = syrove

    @staticmethod
    def sestavit_poradi(vertikaly: Sequence[Mapping]) -> dict[str, int]:
        return {c["a"]: i for i, c in enumerate(vertikaly)}

    def vypsat_aktivace(self, token: Mapping) -> list[str]:
        return self.seradit_kanonicky(self.odfiltrovat_typy(token["acts"]))

    def odfiltrovat_typy(self, acts: Sequence[str]) -> list[str]:
        """Vypnutý významový typ musí zmizet i z pole, ne jen z vektoru —
        jinak pole přestane být obrázkem šablony, kterou ukazuje panel."""
        if self.typy:
            return list(acts)
        return [a for a in acts if not a.startswith("Typ=")]

    def seradit_kanonicky(self, acts: Iterable[str]) -> list[str]:
        """Pořadí je významné: táž sada jinak seřazená by dala jinou
        šablonu. Matice metadat přidává na konec, tohle to srovná."""
        return sorted(acts, key=lambda a: self.poradi.get(a, 1 << 30))

    def je_interpunkce(self, token: Mapping) -> bool:
        return token.get("upos") == "PUNCT"

    def urcit_tvar(self, token: Mapping) -> str:
        forma = token["form"]
        return forma if self.syrove else forma.lower()


class SkladacRetezcem(SkladacVektoru):
    """Vektor jako seznam řetězců „offset:aktivace"."""

    def popsat_slot(self, offset: int, aktivace: Sequence[str]) -> list[str]:
        if not aktivace:
            return [f"{zapsat_offset(offset)}:{PRAZDNO}"]
        return [f"{zapsat_offset(offset)}:{a}" for a in aktivace]

    def slozit_vektor(self, casti: Iterable[Sequence[str]]) -> list[str]:
        return [kus for cast in casti for kus in cast]

    def spocitat_klic(self, vektor: Sequence[str]) -> Hashable:
        return "|".join(vektor)

    def vypsat_vektor(self, vektor: Sequence[str]) -> list[str]:
        return list(vektor)


class SlucovacShodou(Slucovac):
    """Dva vektory jsou tatáž šablona, právě když jsou znak po znaku stejné."""

    def __init__(self) -> None:
        self.predpona = "t"
        self.podle_klice: dict[Hashable, str] = {}
        self.sablony: dict[str, dict] = {}

    def zacit_sadu(self, predpona: str) -> None:
        self.predpona = predpona
        self.podle_klice = {}
        self.sablony = {}

    def zaradit(self, vektor: Any, klic: Hashable) -> str:
        if klic not in self.podle_klice:
            self.podle_klice[klic] = self.zalozit_sablonu(vektor)
        return self.podle_klice[klic]

    def zalozit_sablonu(self, vektor: Any) -> str:
        oznaceni = f"{self.predpona}{len(self.sablony) + 1:02d}"
        self.sablony[oznaceni] = {"vec": list(vektor), "tvary": set(), "radky": []}
        return oznaceni

    def vypsat_sablony(self) -> Mapping[str, dict]:
        return self.sablony
